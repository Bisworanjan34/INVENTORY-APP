# apps.py
from django.apps import AppConfig


class YourAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"  # Apne app ka sahi naam yahan daalo

    def ready(self):
        import inventory.signals  # Yahan signals import karo
