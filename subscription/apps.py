import os
import sys
import threading
import time

from django.apps import AppConfig


class SubcriptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscription"

    def ready(self):
        # Import signals to register them
        try:
            import subscription.signals  # noqa: F401
        except Exception:
            pass
