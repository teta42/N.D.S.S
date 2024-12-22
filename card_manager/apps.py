from django.apps import AppConfig


class CardManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'card_manager'
    verbose_name = 'Card manager'
    path = '../card_manager'