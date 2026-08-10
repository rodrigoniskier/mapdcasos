from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import AIJob, Encounter


class Command(BaseCommand):
    help = 'Manutenção manual do perfil gratuito: backup, limpeza de jobs e estado Gemini expirável.'

    def add_arguments(self, parser):
        parser.add_argument('--job-days', type=int, default=7, help='Reter jobs terminais por N dias (padrão: 7).')
        parser.add_argument('--keep-backups', type=int, default=2, help='Quantidade de backups SQLite a manter (padrão: 2).')
        parser.add_argument('--skip-backup', action='store_true', help='Não criar backup antes da limpeza.')

    def handle(self, *args, **options):
        if not options['skip_backup']:
            call_command('backup_sqlite', keep=max(1, options['keep_backups']))

        now = timezone.now()
        terminal = [AIJob.Status.COMPLETED, AIJob.Status.FAILED, AIJob.Status.CANCELLED]
        jobs_cutoff = now - timedelta(days=max(1, options['job_days']))
        deleted_jobs, _ = AIJob.objects.filter(status__in=terminal, completed_at__lt=jobs_cutoff).delete()

        # No nível gratuito da Interactions API, o estado armazenado é temporário.
        # Limpar IDs locais antigos faz o próximo turno reconstruir o contexto a
        # partir do transcript persistido no nosso banco, em vez de depender de
        # um ID remoto possivelmente expirado.
        interaction_cutoff = now - timedelta(hours=20)
        stale_interactions = (
            Encounter.objects.filter(updated_at__lt=interaction_cutoff)
            .exclude(patient_interaction_id='')
            .update(patient_interaction_id='', patient_interaction_model='')
        )

        # Cache em arquivo é descartável; limpar aqui evita crescimento indefinido
        # e remove contadores/circuit breakers antigos entre sessões de uso.
        cache.clear()

        self.stdout.write(self.style.SUCCESS('Manutenção do perfil gratuito concluída.'))
        self.stdout.write(f'AIJobs terminais removidos: {deleted_jobs}')
        self.stdout.write(f'Estados remotos antigos limpos: {stale_interactions}')
        self.stdout.write('Cache local limpo: sim')
