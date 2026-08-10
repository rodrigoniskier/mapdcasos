import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def _client():
    if not settings.GEMINI_API_KEY:
        return None
    from google import genai
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _transcript(encounter, limit=36):
    messages = list(encounter.messages.all().order_by('-created_at', '-id')[:limit])
    messages.reverse()
    labels = {
        'STUDENT': 'ALUNO', 'PATIENT': 'PACIENTE', 'PRECEPTOR': 'PRECEPTOR',
        'TUTOR': 'TUTOR', 'SYSTEM': 'SISTEMA',
    }
    return '\n'.join(f"{labels.get(m.role, m.role)}: {m.content}" for m in messages)


def _case_packet(case):
    return json.dumps({
        'paciente': {'nome': case.patient_name, 'idade': case.age, 'sexo': case.sex},
        'queixa_inicial': case.complaint,
        'patogeno': case.pathogen,
        'diagnostico_alvo': case.diagnosis,
        'ficha_mestra': case.master_context,
        'conduta_esperada': case.expected_management,
        'sinais_de_alarme': case.red_flags,
        'conceito_ancora': case.concept_anchor,
    }, ensure_ascii=False, indent=2)


def _text(prompt: str, fallback: str) -> str:
    client = _client()
    if client is None:
        return fallback
    try:
        interaction = client.interactions.create(model=settings.GEMINI_MODEL, input=prompt)
        return (interaction.output_text or fallback).strip()
    except Exception:
        logger.exception('Erro ao consultar Gemini')
        return fallback


def _structured(prompt: str, schema: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    client = _client()
    if client is None:
        return fallback
    try:
        interaction = client.interactions.create(
            model=settings.GEMINI_MODEL,
            input=prompt,
            response_format={'type': 'text', 'mime_type': 'application/json', 'schema': schema},
        )
        data = json.loads(interaction.output_text)
        return data if isinstance(data, dict) else fallback
    except Exception:
        logger.exception('Erro ao consultar Gemini com saída estruturada')
        return fallback


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
        'reply': 'No momento o paciente virtual não conseguiu responder. Verifique a configuração da API Gemini e tente novamente.',
        'is_treatment': False,
        'treatment_assessment': 'NOT_APPLICABLE',
    }
    result = _structured(prompt, schema, fallback)
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
    return _text(prompt, 'Revise o que já foi perguntado e procure identificar qual informação ainda mudaria de forma importante sua hipótese ou sua conduta.')


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
    return _text(prompt, 'Pense em qual característica biológica do agente ou da resposta do hospedeiro explicaria os achados que você já identificou.')


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
        'care_summary': 'A avaliação automática não pôde ser concluída. Verifique a configuração da API Gemini.',
        'strengths': [],
        'reinforcement': ['Repetir a avaliação após restabelecer a conexão com a IA.'],
        'study_topics': [encounter.case.concept_anchor or 'Revisão do caso'],
        'domains': {'comunicacao': 0, 'anamnese': 0, 'sinais_alarme': 0, 'investigacao': 0, 'raciocinio': 0, 'conduta': 0, 'seguimento': 0},
    }
    return _structured(prompt, schema, fallback)
