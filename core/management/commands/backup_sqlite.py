import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = 'Cria backup verificado do SQLite e mantém apenas os backups mais recentes.'

    def add_arguments(self, parser):
        parser.add_argument('--keep', type=int, default=2, help='Quantidade de backups a manter (padrão: 2).')

    def handle(self, *args, **options):
        if connection.vendor != 'sqlite':
            raise CommandError('Este comando é exclusivo do modo SQLite.')

        keep = max(1, options['keep'])
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            raise CommandError(f'Banco SQLite não encontrado: {db_path}')

        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = timezone.localtime().strftime('%Y%m%d-%H%M%S')
        target = backup_dir / f'mapdcasos-{stamp}.sqlite3'

        # Libera a conexão do Django e usa a API oficial de backup do SQLite,
        # que produz uma cópia consistente mesmo com o banco em uso.
        connection.close()
        source = sqlite3.connect(str(db_path), timeout=30)
        destination = sqlite3.connect(str(target), timeout=30)
        try:
            with destination:
                source.backup(destination)
        finally:
            destination.close()
            source.close()

        # Não considerar backup válido sem uma verificação mínima de integridade.
        verify = sqlite3.connect(str(target), timeout=30)
        try:
            result = verify.execute('PRAGMA integrity_check').fetchone()
        finally:
            verify.close()
        if not result or result[0] != 'ok':
            target.unlink(missing_ok=True)
            raise CommandError(f'Falha na verificação de integridade do backup: {result!r}')

        backups = sorted(backup_dir.glob('mapdcasos-*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)
        removed = 0
        for old in backups[keep:]:
            old.unlink(missing_ok=True)
            removed += 1

        size_mb = target.stat().st_size / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f'Backup OK: {target} ({size_mb:.2f} MiB)'))
        self.stdout.write(f'Retenção: {keep} arquivo(s); removidos: {removed}.')
