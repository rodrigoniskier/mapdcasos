from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'Audita o MAPD Casos contra os gates críticos do Protocolo RN.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Retorna erro se houver qualquer gate crítico de produção pendente.',
        )

    def handle(self, *args, **options):
        checks = []

        def add(name, ok, detail, severity='P1'):
            checks.append((name, bool(ok), detail, severity))

        add('Ambiente production', settings.APP_ENV == 'production', f'APP_ENV={settings.APP_ENV}', 'P1')
        add('DEBUG desligado', not settings.DEBUG, f'DEBUG={settings.DEBUG}', 'P0')
        add('Secret key não padrão', settings.SECRET_KEY != 'dev-only-change-me', 'DJANGO_SECRET_KEY', 'P0')
        add('PostgreSQL', connection.vendor == 'postgresql', f'backend={connection.vendor}', 'P1')
        add('Cache compartilhado Redis', bool(settings.REDIS_URL), 'REDIS_URL configurada' if settings.REDIS_URL else 'cache em arquivo', 'P1')
        add('Gemini configurada', bool(settings.GEMINI_API_KEY) or not settings.AI_ENABLED, f'AI_ENABLED={settings.AI_ENABLED}', 'P1')
        add('AI Gateway habilitado', settings.AI_ENABLED, f'AI_ENABLED={settings.AI_ENABLED}', 'P1')
        add('Fila/background', settings.AI_BACKGROUND_ENABLED, f'AI_BACKGROUND_ENABLED={settings.AI_BACKGROUND_ENABLED}', 'P1')
        add('Rate limit global', settings.AI_RATE_LIMIT_GLOBAL_PER_MINUTE > 0, str(settings.AI_RATE_LIMIT_GLOBAL_PER_MINUTE), 'P1')
        add('Backpressure global', settings.AI_MAX_PENDING_GLOBAL > 0, str(settings.AI_MAX_PENDING_GLOBAL), 'P1')
        add('Retry limitado', 1 <= settings.GEMINI_RETRY_ATTEMPTS <= 5, str(settings.GEMINI_RETRY_ATTEMPTS), 'P1')
        add('Schema repair limitado', 0 <= settings.AI_SCHEMA_REPAIR_ATTEMPTS <= 2, str(settings.AI_SCHEMA_REPAIR_ATTEMPTS), 'P1')
        add('Circuit breaker', settings.GEMINI_CIRCUIT_FAILURE_THRESHOLD >= 2, str(settings.GEMINI_CIRCUIT_FAILURE_THRESHOLD), 'P1')
        add('Token budget chat', settings.GEMINI_CHAT_MAX_OUTPUT_TOKENS <= 1024, str(settings.GEMINI_CHAT_MAX_OUTPUT_TOKENS), 'P2')
        add('Token budget avaliação', settings.GEMINI_EVALUATION_MAX_OUTPUT_TOKENS <= 3000, str(settings.GEMINI_EVALUATION_MAX_OUTPUT_TOKENS), 'P2')

        failed = []
        self.stdout.write(self.style.MIGRATE_HEADING('MAPD Casos — Production Readiness / Protocolo RN'))
        for name, ok, detail, severity in checks:
            marker = 'OK' if ok else 'PENDENTE'
            style = self.style.SUCCESS if ok else self.style.WARNING
            self.stdout.write(style(f'[{marker}] {severity} — {name}: {detail}'))
            if not ok:
                failed.append((name, severity))

        self.stdout.write('')
        if failed:
            self.stdout.write(self.style.WARNING(f'{len(failed)} gate(s) pendente(s).'))
            if options['strict']:
                raise CommandError('Produção ainda não atende todos os gates do Protocolo RN.')
        else:
            self.stdout.write(self.style.SUCCESS('Todos os gates avaliados estão satisfeitos.'))
