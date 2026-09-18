from django.apps import AppConfig


class ERPintegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ERPintegration'

    def ready(self):
        import ERPintegration.signals
