import os
import sys
import threading
import time

from django.apps import AppConfig


class SubcriptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscription"
