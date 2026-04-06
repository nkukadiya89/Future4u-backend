from decouple import config
import os
import sys
from django.utils import timezone
from django.apps import AppConfig


class CompanyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "company"

    def ready(self):
        if os.environ.get("DJANGO_SETTINGS_MODULE") == "e_switch.settings":
            try:
                from utils.subscription_reminder import send_subscription_reminders

                reminder_time = config("SUBSCRIPTION_EXPIRE_REMINDER_TIME", "09:00")
                current_time = timezone.now().strftime("%H:%M")

                # Log start message

                # Check if current time matches reminder time
                if current_time == reminder_time:
                    from django.core.signals import request_started
                    from django.dispatch import receiver

                    @receiver(request_started)
                    def run_subscription_reminder(sender, **kwargs):
                        send_subscription_reminders()
                        # Disconnect after running once
                        request_started.disconnect(run_subscription_reminder)

                else:
                    pass

                if not config("RUN_MAIN_APP", None):
                    from django.core.signals import request_started
                    from django.dispatch import receiver

                    @receiver(request_started)
                    def run_startup_subscription_check(sender, **kwargs):
                        send_subscription_reminders()
                        request_started.disconnect(run_startup_subscription_check)

            except Exception as e:
                import traceback

                traceback.print_exc()
