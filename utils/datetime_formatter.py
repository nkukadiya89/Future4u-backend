from datetime import datetime

from django.utils import timezone


def format_datetime(value):
    if value is None:
        return None

    if hasattr(value, "astimezone"):
        if timezone.is_aware(value):
            value = timezone.localtime(value)

    if isinstance(value, datetime):
        # return value.strftime("%d-%m-%Y %I:%M %p")
        return value.strftime("%d-%m-%Y %H:%M")

    return value
