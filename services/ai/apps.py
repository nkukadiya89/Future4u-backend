from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.ai"
    label = "services_ai"
    verbose_name = "AI Service"
