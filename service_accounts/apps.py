from django.apps import AppConfig


class ServiceAccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'service_accounts'

    def ready(self):
        import service_accounts.signals  # Импортируем сигналы