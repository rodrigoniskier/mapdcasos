import json
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Type

from django.conf import settings
from django.core.cache import cache
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class AIErrorType(StrEnum):
    CONFIG = 'AI_CONFIG_ERROR'
    AUTH = 'AI_AUTH_ERROR'
    CLIENT = 'AI_CLIENT_ERROR'
    MODEL = 'AI_MODEL_UNAVAILABLE'
    QUOTA = 'AI_QUOTA_ERROR'
    TRANSIENT = 'AI_TRANSIENT_ERROR'
    SAFETY = 'AI_SAFETY_ERROR'
    SCHEMA = 'AI_OUTPUT_SCHEMA_ERROR'
    EMPTY = 'AI_EMPTY_OUTPUT'
    CIRCUIT_OPEN = 'AI_CIRCUIT_OPEN'
    UNKNOWN = 'AI_UNKNOWN_ERROR'


@dataclass(frozen=True)
class TaskPolicy:
    primary_model: str
    fallback_model: str
    compatibility_model: str
    max_output_tokens: int
    thinking_level: str


@dataclass
class GatewayResult:
    ok: bool
    interaction_id: str = ''
    status: str = ''
    model: str = ''
    output_text: str = ''
    error_type: str = ''
    error_code: str = ''
    error_message: str = ''
    fallback_used: bool = False
    tokens_input: int | None = None
    tokens_output: int | None = None
    duration_ms: int = 0


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    retry_after: int = 0
    reason: str = ''


def policy_for(kind: str) -> TaskPolicy:
    if kind == 'EVALUATION':
        return TaskPolicy(
            primary_model=settings.GEMINI_EVALUATION_MODEL,
            fallback_model=settings.GEMINI_EVALUATION_FALLBACK_MODEL,
            compatibility_model='gemini-2.5-flash',
            max_output_tokens=settings.GEMINI_EVALUATION_MAX_OUTPUT_TOKENS,
            thinking_level=settings.GEMINI_EVALUATION_THINKING_LEVEL,
        )
    return TaskPolicy(
        primary_model=settings.GEMINI_CHAT_MODEL,
        fallback_model=settings.GEMINI_CHAT_FALLBACK_MODEL,
        compatibility_model='gemini-2.5-flash-lite',
        max_output_tokens=settings.GEMINI_CHAT_MAX_OUTPUT_TOKENS,
        thinking_level=settings.GEMINI_CHAT_THINKING_LEVEL,
    )


@lru_cache(maxsize=1)
def _client():
    if not settings.GEMINI_API_KEY:
        return None
    from google import genai
    from google.genai import types

    retry_options = types.HttpRetryOptions(
        attempts=settings.GEMINI_RETRY_ATTEMPTS,
        initial_delay=0.8,
        max_delay=6.0,
        exp_base=2.0,
        jitter=1.0,
        http_status_codes=[408, 429, 500, 502, 503, 504],
    )
    return genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(
            api_version=settings.GEMINI_API_VERSION,
            timeout=settings.GEMINI_HTTP_TIMEOUT_MS,
            retry_options=retry_options,
        ),
    )


def _value(value):
    return getattr(value, 'value', value)


def _status_code(exc: Exception) -> int | None:
    for attr in ('status_code', 'code'):
        value = _value(getattr(exc, attr, None))
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    response = getattr(exc, 'response', None)
    value = _value(getattr(response, 'status_code', None))
    return value if isinstance(value, int) else None


def classify_exception(exc: Exception) -> AIErrorType:
    code = _status_code(exc)
    text = f'{type(exc).__name__} {exc}'.lower()
    if code in {401, 403}:
        return AIErrorType.AUTH
    if code == 404 and 'model' in text and ('not found' in text or 'not_found' in text):
        # A documented model can still be unavailable to a specific project or
        # rollout cohort. Treat that as a routing condition, not as a terminal
        # malformed-request error, so the Model Router can continue safely.
        return AIErrorType.MODEL
    if code == 429:
        return AIErrorType.QUOTA
    if code == 408 or (code is not None and 500 <= code <= 599):
        return AIErrorType.TRANSIENT
    if code is not None and 400 <= code <= 499:
        return AIErrorType.CLIENT
    if any(token in text for token in ('safety', 'blocked', 'recitation', 'prohibited content')):
        return AIErrorType.SAFETY
    if any(token in text for token in ('timeout', 'timed out', 'connection', 'network', 'temporarily unavailable')):
        return AIErrorType.TRANSIENT
    return AIErrorType.UNKNOWN


def _safe_error_message(exc: Exception) -> str:
    text = str(exc).replace('\n', ' ').strip()
    return text[:450]


def _cache_increment(key: str, timeout: int) -> int:
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return int(cache.incr(key))
    except (ValueError, TypeError):
        cache.set(key, 1, timeout=timeout)
        return 1


def check_rate_limit(user_id: int, kind: str) -> RateDecision:
    now = int(time.time())
    window = now // 60
    ttl = 70
    dimensions = [
        (f'rn:ai:rate:global:{window}', settings.AI_RATE_LIMIT_GLOBAL_PER_MINUTE, 'global'),
        (f'rn:ai:rate:user:{user_id}:{window}', settings.AI_RATE_LIMIT_USER_PER_MINUTE, 'user'),
        (f'rn:ai:rate:kind:{kind}:{window}', settings.AI_RATE_LIMIT_KIND_PER_MINUTE, 'kind'),
    ]
    for key, limit, reason in dimensions:
        if limit <= 0:
            continue
        value = _cache_increment(key, ttl)
        if value > limit:
            return RateDecision(False, retry_after=max(1, 60 - (now % 60)), reason=reason)
    return RateDecision(True)


def _breaker_open_key(model: str) -> str:
    return f'rn:ai:breaker:{model}:open'


def _breaker_fail_key(model: str) -> str:
    return f'rn:ai:breaker:{model}:failures'


def circuit_is_open(model: str) -> bool:
    return bool(model and cache.get(_breaker_open_key(model)))


def circuit_record_success(model: str) -> None:
    if model:
        cache.delete_many([_breaker_open_key(model), _breaker_fail_key(model)])


def circuit_record_failure(model: str, error_type: AIErrorType) -> None:
    if not model or error_type not in {AIErrorType.TRANSIENT, AIErrorType.QUOTA, AIErrorType.UNKNOWN}:
        return
    failures = _cache_increment(
        _breaker_fail_key(model),
        settings.GEMINI_CIRCUIT_COOLDOWN_SECONDS * 2,
    )
    if failures >= settings.GEMINI_CIRCUIT_FAILURE_THRESHOLD:
        cache.set(
            _breaker_open_key(model),
            True,
            timeout=settings.GEMINI_CIRCUIT_COOLDOWN_SECONDS,
        )
        logger.warning('RN circuit breaker opened model=%s failures=%s', model, failures)


def circuit_state(model: str) -> dict:
    return {
        'model': model,
        'open': circuit_is_open(model),
        'failures': int(cache.get(_breaker_fail_key(model), 0) or 0),
    }


def _model_candidates(policy: TaskPolicy, force_model: str = ''):
    if force_model:
        yield force_model, force_model != policy.primary_model
        return
    seen = set()
    for model, fallback_used in (
        (policy.primary_model, False),
        (policy.fallback_model, True),
        (policy.compatibility_model, True),
    ):
        if model and model not in seen:
            seen.add(model)
            yield model, fallback_used


def _fallback_allowed(error_type: AIErrorType) -> bool:
    if error_type in {
        AIErrorType.MODEL,
        AIErrorType.TRANSIENT,
        AIErrorType.UNKNOWN,
        AIErrorType.SCHEMA,
        AIErrorType.EMPTY,
    }:
        return True
    if error_type == AIErrorType.QUOTA:
        return settings.GEMINI_FALLBACK_ON_QUOTA
    return False


def _interaction_usage(interaction) -> tuple[int | None, int | None]:
    usage = getattr(interaction, 'usage', None)
    if not usage:
        return None, None
    input_tokens = _value(getattr(usage, 'total_input_tokens', None))
    output_tokens = _value(getattr(usage, 'total_output_tokens', None))
    return (
        int(input_tokens) if isinstance(input_tokens, (int, float)) else None,
        int(output_tokens) if isinstance(output_tokens, (int, float)) else None,
    )


def _status(interaction) -> str:
    value = _value(getattr(interaction, 'status', ''))
    return str(value or '').lower()


def _generation_config(model: str, policy: TaskPolicy) -> dict:
    config = {'max_output_tokens': policy.max_output_tokens}
    # Gemini 3.x uses thinking_level. Gemini 2.5 has a different thinking
    # control surface; omit it in the compatibility tier rather than risk a
    # 400 caused by a generation parameter unsupported by that family.
    if not model.startswith('gemini-2.5-'):
        config['thinking_level'] = policy.thinking_level
    return config


def start_background_interaction(
    *,
    kind: str,
    system_instruction: str,
    input_text: str,
    schema_model: Type[BaseModel],
    previous_interaction_id: str = '',
    force_model: str = '',
) -> GatewayResult:
    if not settings.AI_ENABLED:
        return GatewayResult(False, error_type=AIErrorType.CONFIG, error_message='AI desabilitada por kill switch.')
    if kind == 'PATIENT' and not settings.PATIENT_AI_ENABLED:
        return GatewayResult(False, error_type=AIErrorType.CONFIG, error_message='Paciente virtual desabilitado por kill switch.')
    if kind == 'EVALUATION' and not settings.EVALUATION_AI_ENABLED:
        return GatewayResult(False, error_type=AIErrorType.CONFIG, error_message='Avaliação por IA desabilitada por kill switch.')

    client = _client()
    if client is None:
        return GatewayResult(False, error_type=AIErrorType.CONFIG, error_message='GEMINI_API_KEY ausente.')

    policy = policy_for(kind)
    last_result = GatewayResult(False, error_type=AIErrorType.UNKNOWN)
    for model, fallback_used in _model_candidates(policy, force_model=force_model):
        if circuit_is_open(model):
            last_result = GatewayResult(
                False,
                model=model,
                error_type=AIErrorType.CIRCUIT_OPEN,
                error_message='Circuit breaker temporariamente aberto.',
                fallback_used=fallback_used,
            )
            continue
        started = time.monotonic()
        try:
            kwargs = {
                'model': model,
                'system_instruction': system_instruction,
                'input': input_text,
                'background': bool(settings.AI_BACKGROUND_ENABLED),
                # Stored independently of background mode: previous_interaction_id
                # chaining for patient conversation continuity needs the interaction
                # retrievable server-side even when we complete synchronously.
                'store': True,
                'generation_config': _generation_config(model, policy),
                'response_format': {
                    'type': 'text',
                    'mime_type': 'application/json',
                    'schema': schema_model.model_json_schema(),
                },
            }
            if previous_interaction_id:
                kwargs['previous_interaction_id'] = previous_interaction_id
            interaction = client.interactions.create(**kwargs)
            duration_ms = int((time.monotonic() - started) * 1000)
            circuit_record_success(model)
            tokens_input, tokens_output = _interaction_usage(interaction)
            return GatewayResult(
                True,
                interaction_id=str(getattr(interaction, 'id', '') or ''),
                status=_status(interaction),
                model=model,
                output_text=(getattr(interaction, 'output_text', '') or '').strip(),
                fallback_used=fallback_used,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            error_type = classify_exception(exc)
            circuit_record_failure(model, error_type)
            last_result = GatewayResult(
                False,
                model=model,
                error_type=error_type,
                error_code=str(_status_code(exc) or ''),
                error_message=_safe_error_message(exc),
                fallback_used=fallback_used,
                duration_ms=duration_ms,
            )
            logger.warning(
                'RN AI start failed kind=%s model=%s api=%s error_type=%s code=%s duration_ms=%s error=%s',
                kind,
                model,
                settings.GEMINI_API_VERSION,
                error_type,
                last_result.error_code,
                duration_ms,
                last_result.error_message,
            )
            if not _fallback_allowed(error_type):
                break
    return last_result


def poll_interaction(interaction_id: str, model: str = '') -> GatewayResult:
    client = _client()
    if client is None:
        return GatewayResult(False, error_type=AIErrorType.CONFIG, error_message='GEMINI_API_KEY ausente.')
    started = time.monotonic()
    try:
        interaction = client.interactions.get(interaction_id)
        duration_ms = int((time.monotonic() - started) * 1000)
        status = _status(interaction)
        tokens_input, tokens_output = _interaction_usage(interaction)
        if status == 'failed':
            error = getattr(interaction, 'error', None)
            code = _value(getattr(error, 'code', None))
            message = str(getattr(error, 'message', '') or 'A interação Gemini falhou.')
            synthetic = RuntimeError(message)
            if isinstance(code, int):
                setattr(synthetic, 'status_code', code)
            error_type = classify_exception(synthetic)
            circuit_record_failure(model, error_type)
            logger.warning(
                'RN AI background failed interaction=%s model=%s api=%s error_type=%s code=%s error=%s',
                interaction_id,
                model,
                settings.GEMINI_API_VERSION,
                error_type,
                code or '',
                message[:450],
            )
            return GatewayResult(
                False,
                interaction_id=interaction_id,
                status=status,
                model=model,
                error_type=error_type,
                error_code=str(code or ''),
                error_message=message[:450],
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                duration_ms=duration_ms,
            )
        if status == 'completed':
            circuit_record_success(model)
        return GatewayResult(
            True,
            interaction_id=interaction_id,
            status=status,
            model=model,
            output_text=(getattr(interaction, 'output_text', '') or '').strip(),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        error_type = classify_exception(exc)
        circuit_record_failure(model, error_type)
        safe_message = _safe_error_message(exc)
        logger.warning(
            'RN AI poll failed interaction=%s model=%s api=%s error_type=%s code=%s duration_ms=%s error=%s',
            interaction_id,
            model,
            settings.GEMINI_API_VERSION,
            error_type,
            _status_code(exc) or '',
            duration_ms,
            safe_message,
        )
        return GatewayResult(
            False,
            interaction_id=interaction_id,
            model=model,
            error_type=error_type,
            error_code=str(_status_code(exc) or ''),
            error_message=safe_message,
            duration_ms=duration_ms,
        )


def validate_output(output_text: str, schema_model: Type[BaseModel]) -> tuple[dict | None, GatewayResult | None]:
    if not (output_text or '').strip():
        return None, GatewayResult(False, error_type=AIErrorType.EMPTY, error_message='Gemini retornou saída vazia.')
    try:
        parsed = schema_model.model_validate_json(output_text)
        return parsed.model_dump(), None
    except (ValidationError, json.JSONDecodeError, ValueError) as exc:
        return None, GatewayResult(
            False,
            error_type=AIErrorType.SCHEMA,
            error_message=str(exc).replace('\n', ' ')[:450],
        )
