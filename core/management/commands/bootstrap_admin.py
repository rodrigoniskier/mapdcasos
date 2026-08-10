import os
from django.core.management.base import BaseCommand, CommandError
from core.models import User


class Command(BaseCommand):
    help = 'Cria ou atualiza o superusuário único do MAPD Casos a partir das variáveis de ambiente.'

    def handle(self, *args, **options):
        username = os.getenv('SUPERUSER_USERNAME', 'rodrigo').strip()
        name = os.getenv('SUPERUSER_NAME', 'Prof. Rodrigo Niskier').strip()
        email = os.getenv('SUPERUSER_EMAIL', '').strip()
        password = os.getenv('SUPERUSER_PASSWORD', '')
        if not password:
            raise CommandError('Defina SUPERUSER_PASSWORD no arquivo .env antes de executar este comando.')

        existing_other = User.objects.filter(is_superuser=True).exclude(username=username)
        if existing_other.exists():
            names = ', '.join(existing_other.values_list('username', flat=True))
            raise CommandError(f'Já existe outro superusuário ({names}). Remova-o antes de continuar para manter o modelo de superusuário único.')

        user, _ = User.objects.get_or_create(username=username)
        parts = name.split(maxsplit=1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = email
        user.role = User.Role.PROFESSOR
        user.rgm = None
        user.turma = ''
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Superusuário {username} pronto.'))
