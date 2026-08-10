from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def rn_production_checks(app_configs, **kwargs):
    """Protocol RN deployment checks.

    These are warnings rather than hard errors so bootstrap/test deployments keep
    working. The production_readiness command can enforce them strictly before a
    classroom release.
    """
    issues = []
    if settings.APP_ENV != 'production':
        return issues

    database = settings.DATABASES['default']
    if database.get('ENGINE') == 'django.db.backends.sqlite3':
        issues.append(
            Warning(
                'Produção está usando SQLite; concorrência de escrita pode causar locks em turma.',
                hint='Configure DATABASE_URL apontando para PostgreSQL antes do uso multiusuário.',
                id='RN.W001',
            )
        )

    if not settings.REDIS_URL:
        issues.append(
            Warning(
                'Produção está sem Redis compartilhado; rate limit e circuit breaker usam cache em arquivo.',
                hint='Configure REDIS_URL quando houver múltiplos web workers.',
                id='RN.W002',
            )
        )

    if not settings.GEMINI_API_KEY and settings.AI_ENABLED:
        issues.append(
            Warning(
                'AI_ENABLED está ativo, mas nenhuma GEMINI_API_KEY foi carregada.',
                hint='Defina GEMINI_API_KEY no ambiente ou desligue AI_ENABLED.',
                id='RN.W003',
            )
        )

    if settings.SECRET_KEY == 'dev-only-change-me':
        issues.append(
            Warning(
                'DJANGO_SECRET_KEY ainda usa o valor padrão de desenvolvimento.',
                hint='Defina uma chave longa, aleatória e exclusiva para produção.',
                id='RN.W004',
            )
        )

    if settings.DEBUG:
        issues.append(
            Warning(
                'DEBUG está ativo em ambiente de produção.',
                hint='Defina DJANGO_DEBUG=False.',
                id='RN.W005',
            )
        )

    if settings.AI_BACKGROUND_ENABLED and not settings.AI_ENABLED:
        issues.append(
            Warning(
                'AI_BACKGROUND_ENABLED está ativo enquanto AI_ENABLED está desligado.',
                hint='Alinhe os kill switches para evitar configuração ambígua.',
                id='RN.W006',
            )
        )

    return issues
