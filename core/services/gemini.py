import json
import logging
from functools import lru_cache
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_RETRYABLE_HTTP_CODES = [408, 429, 500, 502, 503, 504]
_PERMANENT_HTTP_CODES = {400, 401, 403}


@lru_cache(maxsize=1)
def _client():
    """Reuse one SDK client per web worker so HTTP connections are pooled."""
    if not settings.GEMINI_API_KEY:
        return None

    from google import genai
    from google.genai import types

    retry_options = types.HttpRetryOptions(
        attempts=settings.GEMINI_RETRY_ATTEMPTS,
        initial_delay=0.6,
        max_delay=4.0,
        exp_base=2.0,
        jitter=1.0,
        http_status_codes=_RETRYABLE_HTTP_CODES,
    )
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(retry_options=retry_options),
    )


def _status_code(exc: Exception) -> int | None:
    for attr in ('status_code', 'code'):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, 'response', None)
    value = getattr(response, 'status_code', None)
    return value if isinstance(value, int) else None


def _can_try_fallback(exc: Exception) -> bool:
    code = _status_code(exc)
    return code not in _PERMANENT_HTTP_CODES


def _model_candidates(primary: str, fallback: str):
    seen = set()
    for model in (primary, fallback):
        if model and model not in seen:
            seen.add(model)
            yield model


def _transcript(encounter, limit=24):
    messages = list(encounter.messages.all().order_by('-created_at', '-id')[:limit])
    messages.reverse()
    labels = {
        'STUDENT': 'ALUNO', 'PATIENT': 'PACIENTE', 'PRECEPTOR': 'PRECEPTOR',
        'TUTOR': 'TUTOR', 'SYSTEM': 'SISTEMA',
    }
    return '\n'.join(f"{labels.get(m.role, m.role)}: {m.content}" for m in messages)


def _case_packet(case):
    # Compact JSON reduces repeated input tokens on every conversational turn.
    return json.dumps({
        'paciente': {'nome': case.patient_name, 'idade': case.age, 'sexo': case.sex},
        'queixa_inicial': case.complaint,
        'patogeno': case.pathogen,
        'diagnostico_alvo': case.diagnosis,
        'ficha_mestra': case.master_context,
        'conduta_esperada': case.expected_management,
        'sinais_de_alarme': case.red_flags,
        'conceito_ancora': case.concept_anchor,
    }, ensure_ascii=False, separators=(',', ':'))


def _text(prompt: str, fallback: str, *, primary_model: str, fallback_model: str) -> str:
    client = _client()
    if client is None:
        logger.error('GEMINI_API_KEY ausente.')
        return fallback

    last_exc = None
    for model in _model_candidates(primary_model, fallback_model):
        try:
            interaction = client.interactions.create(model=model, input=prompt)
            text = (interaction.output_text or '').strip()
            if text:
                return text
            raise ValueError('Gemini retornou texto vazio.')
        except Exception as exc:
            last_exc = exc
            logger.warning(
                'Falha Gemini model=%s status=%s type=%s',
                model, _status_code(exc), type(exc).__name__,
                exc_info=True,
            )
            if not _can_try_fallback(exc):
                break

    if last_exc:
        logger.error('Todos os modelos Gemini falharam para resposta textual.')
    return fallback


def _structured(
    prompt: str,
    schema: dict[str, Any],
    fallback: dict[str, Any],
    *,
    primary_model: str,
    fallback_model: str,
) -> dict[str, Any]:
    client = _client()
    if client is None:
        logger.error('GEMINI_API_KEY ausente.')
        result = dict(fallback)
        result['_service_unavailable'] = True
        return result

    for model in _model_candidates(primary_model, fallback_model):
        try:
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                response_format={
                    'type': 'text',
                    'mime_type': 'application/json',
                    'schema': schema,
                },
            )
            data = json.loads(interaction.output_text or '')
            if not isinstance(data, dict):
                raise ValueError('Saída estruturada não é um objeto JSON.')
            data['_service_unavailable'] = False
            data['_model_used'] = model
            return data
        except Exception as exc:
            logger.warning(
                'Falha Gemini structured model=%s status=%s type=%s',
                model, _status_code(exc), type(exc).__name__,
                exc_info=True,
            )
            if not _can_try_fallback(exc):
                break

    result = dict(fallback)
    result['_service_unavailable'] = True
    return result


def patient_reply(encounter, student_message: str) -> dict[str, Any]:
    case = encounter.case
    prompt = f"""
Você interpreta EXCLUSIVAMENTE o paciente de uma simulação clínica educacional de Atenção Primária à Saúde do SUS.

REGRAS ABSOLUTAS:
1. A ficha-mestra abaixo é a única verdade do caso. Nunca invente sintoma, exposição, antecedente, exame ou resultado que a contradiga.
2. Não revele diagnóstico, patógeno, gabarito, conduta esperada nem raciocínio interno.
3. Responda como paciente, em linguagem natural compatível com idade e contexto. Dê apenas as informações que seriam espontâneas ou que foram perguntadas.
4. Quando o aluno pedir exame físico ou resultado de exame complementar, forneça somente os dados previstos na ficha-mestra. Se o dado não estiver previsto, diga de modo natural que ele não está disponível naquele momento.
5. Se a última mensagem contiver uma PRESCRIÇÃO/CONDUTA TERAPÊUTICA concreta, avalie-a contra a conduta esperada. O paciente deve agradecer e, na mesma resposta, informar de forma breve o desfecho após alguns dias.
6. Se a conduta estiver inadequada, transforme o final da resposta em retorno do paciente com persistência, piora plausível ou ausência de resposta coerente com a ficha. Não crie eventos graves não previstos.
7. Não ensine medicina ao aluno na voz do paciente.

FICHA-MESTRA:
{_case_packet(case)}

CONVERSA ATÉ AGORA:
{_transcript(encounter)}

ÚLTIMA MENSAGEM DO ALUNO:
{student_message}

Classifique se há tratamento concreto e devolva a fala do paciente.
"""
    schema = {
        'type': 'object',
        'properties': {
            'reply': {'type': 'string', 'description': 'Resposta do paciente ao aluno.'},
            'is_treatment': {'type': 'boolean'},
            'treatment_assessment': {
                'type': 'string',
                'enum': ['NOT_APPLICABLE', 'ADEQUATE', 'PARTIAL', 'INADEQUATE'],
            },
        },
        'required': ['reply', 'is_treatment', 'treatment_assessment'],
        'additionalProperties': False,
    }
    fallback = {
        'reply': '',
        'is_treatment': False,
        'treatment_assessment': 'NOT_APPLICABLE',
    }
    result = _structured(
        prompt,
        schema,
        fallback,
        primary_model=settings.GEMINI_CHAT_MODEL,
        fallback_model=settings.GEMINI_CHAT_FALLBACK_MODEL,
    )
    if result.get('treatment_assessment') not in {'NOT_APPLICABLE', 'ADEQUATE', 'PARTIAL', 'INADEQUATE'}:
        result['treatment_assessment'] = 'NOT_APPLICABLE'
    return result


def preceptor_hint(encounter) -> str:
    prompt = f"""
Você é um médico preceptor experiente em APS/SUS acompanhando um estudante em uma simulação clínica.
Analise a ficha-mestra e a conversa. Dê UMA orientação curta que ajude o estudante a perceber uma lacuna relevante da anamnese, exame, raciocínio, segurança ou seguimento.
Não entregue o diagnóstico, o patógeno, o tratamento correto nem a resposta pronta. Prefira perguntas socráticas e pistas acionáveis.
Se houver sinal de alarme negligenciado, priorize-o.

FICHA-MESTRA:
{_case_packet(encounter.case)}

CONVERSA:
{_transcript(encounter)}
"""
    return _text(
        prompt,
        'Revise o que já foi perguntado e procure identificar qual informação ainda mudaria de forma importante sua hipótese ou sua conduta.',
        primary_model=settings.GEMINI_CHAT_MODEL,
        fallback_model=settings.GEMINI_CHAT_FALLBACK_MODEL,
    )


def concept_hint(encounter) -> str:
    prompt = f"""
Você é um tutor de Microbiologia, Imunologia e Patologia para estudantes de Medicina.
Com base na ficha-mestra e APENAS no que já apareceu na conversa, lembre UM conceito essencial que possa destravar o raciocínio do estudante.
Não dê diagnóstico, nome do agente, tratamento correto ou resposta pronta. Formule uma dica conceitual curta, preferencialmente conectando mecanismo biológico a manifestação clínica, epidemiologia ou escolha de exame.

FICHA-MESTRA:
{_case_packet(encounter.case)}

CONVERSA:
{_transcript(encounter)}
"""
    return _text(
        prompt,
        'Pense em qual característica biológica do agente ou da resposta do hospedeiro explicaria os achados que você já identificou.',
        primary_model=settings.GEMINI_CHAT_MODEL,
        fallback_model=settings.GEMINI_CHAT_FALLBACK_MODEL,
    )


def evaluate_encounter(encounter) -> dict[str, Any]:
    prompt = f"""
Você é o preceptor avaliador de uma simulação de APS/SUS. Avalie o atendimento do estudante com base na ficha-mestra, conduta esperada e conversa completa.
Seja criterioso, formativo e transparente. Não premie acertos por acaso sem justificativa. Considere comunicação, anamnese, sinais de alarme, exame/investigação, raciocínio diagnóstico, diferenciais, conduta e orientação/seguimento.
A nota geral deve ser de 0 a 100. O resumo do caso pode agora revelar diagnóstico e patógeno porque o atendimento foi encerrado.

FICHA-MESTRA:
{_case_packet(encounter.case)}

CONVERSA:
{_transcript(encounter, limit=80)}
"""
    schema = {
        'type': 'object',
        'properties': {
            'score': {'type': 'integer', 'minimum': 0, 'maximum': 100},
            'case_summary': {'type': 'string'},
            'care_summary': {'type': 'string'},
            'strengths': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 5},
            'reinforcement': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 5},
            'study_topics': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 6},
            'domains': {
                'type': 'object',
                'properties': {
                    'comunicacao': {'type': 'integer', 'minimum': 0, 'maximum': 10},
                    'anamnese': {'type': 'integer', 'minimum': 0, 'maximum': 20},
                    'sinais_alarme': {'type': 'integer', 'minimum': 0, 'maximum': 15},
                    'investigacao': {'type': 'integer', 'minimum': 0, 'maximum': 15},
                    'raciocinio': {'type': 'integer', 'minimum': 0, 'maximum': 20},
                    'conduta': {'type': 'integer', 'minimum': 0, 'maximum': 15},
                    'seguimento': {'type': 'integer', 'minimum': 0, 'maximum': 5},
                },
                'required': ['comunicacao', 'anamnese', 'sinais_alarme', 'investigacao', 'raciocinio', 'conduta', 'seguimento'],
                'additionalProperties': False,
            },
        },
        'required': ['score', 'case_summary', 'care_summary', 'strengths', 'reinforcement', 'study_topics', 'domains'],
        'additionalProperties': False,
    }
    fallback = {
        'score': 0,
        'case_summary': f'{encounter.case.diagnosis} — {encounter.case.pathogen}.',
        'care_summary': 'A avaliação automática está temporariamente indisponível.',
        'strengths': [],
        'reinforcement': [],
        'study_topics': [encounter.case.concept_anchor or 'Revisão do caso'],
        'domains': {'comunicacao': 0, 'anamnese': 0, 'sinais_alarme': 0, 'investigacao': 0, 'raciocinio': 0, 'conduta': 0, 'seguimento': 0},
    }
    return _structured(
        prompt,
        schema,
        fallback,
        primary_model=settings.GEMINI_EVALUATION_MODEL,
        fallback_model=settings.GEMINI_EVALUATION_FALLBACK_MODEL,
    )
