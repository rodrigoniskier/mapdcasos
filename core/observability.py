import contextvars
import hashlib
import hmac
import logging
import re
import time
import uuid

from django.conf import settings

logger = logging.getLogger(__name__)
_request_id = contextvars.ContextVar('rn_request_id', default='')
_SAFE_REQUEST_ID = re.compile(r'^[A-Za-z0-9._:-]{8,80}$')


def current_request_id() -> str:
    return _request_id.get() or ''


def anonymized_user_id(user) -> str:
    if not getattr(user, 'is_authenticated', False):
        return 'anonymous'
    raw = str(user.pk).encode('utf-8')
    digest = hmac.new(settings.SECRET_KEY.encode('utf-8'), raw, hashlib.sha256).hexdigest()
    return digest[:16]


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = (request.headers.get('X-Request-ID') or '').strip()
        request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else uuid.uuid4().hex
        token = _request_id.set(request_id)
        request.rn_request_id = request_id
        started = time.monotonic()
        status = 500
        try:
            response = self.get_response(request)
            status = response.status_code
            response['X-Request-ID'] = request_id
            return response
        finally:
            duration_ms = int((time.monotonic() - started) * 1000)
            user = getattr(request, 'user', None)
            logger.info(
                'RN_HTTP_METRIC request_id=%s user=%s method=%s path=%s status=%s duration_ms=%s',
                request_id,
                anonymized_user_id(user),
                request.method,
                request.path,
                status,
                duration_ms,
            )
            _request_id.reset(token)
