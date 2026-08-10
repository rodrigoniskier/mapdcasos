from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Register Protocol RN deployment checks.
        from . import checks  # noqa: F401

        # last_login is not used by MAPD Casos. Disabling its signal avoids one
        # database write on every login, which materially reduces SQLite lock
        # contention during classroom access peaks.
        from django.contrib.auth.models import update_last_login
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.disconnect(update_last_login)
