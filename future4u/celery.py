import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "future4u.settings")

app = Celery("future4u")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
