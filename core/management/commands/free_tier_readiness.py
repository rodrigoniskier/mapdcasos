from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from core.models import AIJob, ClinicalCase, User


class Command(BaseCommand):
    help = 'Audita se o MAPD Casos está configurado para piloto controlado no PythonAnywhere gratuito.'

    def add_arguments(self, parser):
        parser.add_argument('--strict', action='store_true', help='Retorna erro se houver ajuste gratuito pendente.')

    def handle(self, *args, **options):
        checks = []
        limits = []

        def add(name, ok, detail, severity='P1'):
            checks.append((name, bool(ok), detail, severity))

        def limit(name, detail):
            limits.append((name, detail))

        add('Ambiente production', settings.APP_ENV == 'production', f'APP_ENV={settings.APP_ENV}', 'P1')
        add('DEBUG desligado', not settings.DEBUG, f'DEBUG={settings.DEBUG}', 'P0')
        add('Secret key não padrão', settings.SECRET_KEY != 'dev-only-change-me', 'DJANGO_SECRET_KEY', 'P0')
        add('Perfil gratuito ativo', settings.FREE_TIER_PROFILE, f'FREE_TIER_PROFILE={settings.FREE_TIER_PROFILE}', 'P1')
        add('Banco acessível', connection.is_usable(), f'backend={connection.vendor}', 'P0')
        active_cases = ClinicalCase.objects.filter(active=True).count()
        add('Carga de casos', active_cases == 80, f'ativos={active_cases}', 'P1')
        superusers = User.objects.filter(is_superuser=True).count()
        add('Superusuário único', superusers == 1, f'total={superusers}', 'P0')
        add('Gemini configurada', bool(settings.GEMINI_API_KEY), 'GEMINI_API_KEY carregada' if settings.GEMINI_API_KEY else 'ausente', 'P1')
        # Background mode's polling endpoint (GET /interactions/{id}) returned 400
        # invalid_request on the preview Interactions API for the production key.
        # Synchronous create() works end to end, so the gate now expects background
        # off; revisit once that preview polling path is verified stable again.
        add('Background Gemini síncrono', not settings.AI_BACKGROUND_ENABLED, f'AI_BACKGROUND_ENABLED={settings.AI_BACKGROUND_ENABLED}', 'P1')
        add('Sessão sem escrita no banco', settings.SESSION_ENGINE == 'django.contrib.sessions.backends.signed_cookies', settings.SESSION_ENGINE, 'P1')
        add('1 job por aluno', settings.AI_MAX_PENDING_PER_USER <= 1, f'AI_MAX_PENDING_PER_USER={settings.AI_MAX_PENDING_PER_USER}', 'P1')
        add('Backpressure conservador', settings.AI_MAX_PENDING_GLOBAL <= 20, f'AI_MAX_PENDING_GLOBAL={settings.AI_MAX_PENDING_GLOBAL}', 'P1')
        add('Rate limit global conservador', settings.AI_RATE_LIMIT_GLOBAL_PER_MINUTE <= 60, f'AI_RATE_LIMIT_GLOBAL_PER_MINUTE={settings.AI_RATE_LIMIT_GLOBAL_PER_MINUTE}', 'P1')
        add('Rate limit por aluno', settings.AI_RATE_LIMIT_USER_PER_MINUTE <= 10, f'AI_RATE_LIMIT_USER_PER_MINUTE={settings.AI_RATE_LIMIT_USER_PER_MINUTE}', 'P1')
        add('Retry limitado', 1 <= settings.GEMINI_RETRY_ATTEMPTS <= 3, f'GEMINI_RETRY_ATTEMPTS={settings.GEMINI_RETRY_ATTEMPTS}', 'P1')
        active_jobs = AIJob.objects.filter(status__in=[AIJob.Status.PENDING, AIJob.Status.RUNNING]).count()
        add('Fila abaixo do limite', active_jobs < settings.AI_MAX_PENDING_GLOBAL, f'ativos={active_jobs}/{settings.AI_MAX_PENDING_GLOBAL}', 'P1')

        if connection.vendor == 'sqlite':
            limit('SQLite', 'aceito apenas para piloto controlado; não é produção multiworker.')
        else:
            add('Banco multiusuário', True, f'backend={connection.vendor}', 'P1')
        if not settings.REDIS_URL:
            limit('Cache em arquivo', 'aceitável com 1 worker; não usar como coordenação de múltiplos workers.')

        failed = []
        self.stdout.write(self.style.MIGRATE_HEADING('MAPD Casos — Free Tier Readiness / Piloto controlado'))
        for name, ok, detail, severity in checks:
            marker = 'OK' if ok else 'AJUSTAR'
            style = self.style.SUCCESS if ok else self.style.WARNING
            self.stdout.write(style(f'[{marker}] {severity} — {name}: {detail}'))
            if not ok:
                failed.append((name, severity))

        for name, detail in limits:
            self.stdout.write(self.style.WARNING(f'[LIMITE GRATUITO] — {name}: {detail}'))

        self.stdout.write('')
        if failed:
            self.stdout.write(self.style.WARNING(f'{len(failed)} ajuste(s) gratuito(s) pendente(s).'))
            if options['strict']:
                raise CommandError('Piloto gratuito ainda possui ajustes de configuração pendentes.')
        else:
            self.stdout.write(self.style.SUCCESS('Piloto gratuito apto dentro das limitações declaradas.'))
            self.stdout.write(self.style.WARNING('Isto não equivale a produção plena nem autoriza teste massivo de turma.'))
