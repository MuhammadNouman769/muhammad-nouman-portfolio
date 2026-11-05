from django.apps import AppConfig


class SubscribersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.subscribers'

    def ready(self):
        from . import signals  # noqa: F401
