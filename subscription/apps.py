import threading
import time
import os
import sys
from django.apps import AppConfig


class SubcriptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscription"

    def ready(self) -> None:
        if not self._should_start_background_tasks():
            return
        self.start_cart_reminder_checker()

    def _should_start_background_tasks(self) -> bool:
        if len(sys.argv) > 1 and sys.argv[1] in {
            "makemigrations",
            "migrate",
            "test",
            "check",
            "shell",
            "createsuperuser",
            "collectstatic",
            "showmigrations",
        }:
            return False
        # Avoid duplicate worker on Django autoreload parent process.
        if len(sys.argv) > 1 and sys.argv[1] == "runserver":
            return os.environ.get("RUN_MAIN") == "true"
        return True

    def check_startup_reminders(self):
        """Check for cart items that already need reminders on startup"""
        try:
            from utils.cart_reminder_checker import check_existing_cart_reminders

            check_existing_cart_reminders()

        except Exception as e:
            print(f"Cart reminder startup check error: {str(e)}")

    def start_cart_reminder_checker(self):
        """Start background thread to check and send cart reminders every 6 hours"""

        def wait_for_db(max_retries=10, delay=5):
            """Wait until the DB is reachable before proceeding."""
            from django.db import connection, OperationalError

            for attempt in range(1, max_retries + 1):
                try:
                    connection.ensure_connection()
                    return True
                except OperationalError as e:
                    print(
                        f"DB not ready (attempt {attempt}/{max_retries}): {e}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            print("DB never became available. Cart reminder worker giving up.")
            return False

        def cart_reminder_worker():
            """Background worker that runs every 6 hours"""
            # Delay initial query until app startup has completed.
            time.sleep(2)

            if not wait_for_db():
                return

            self.check_startup_reminders()
            while True:
                try:
                    from django.db import connection, OperationalError

                    # Re-establish connection if it was dropped (e.g. after long sleep)
                    try:
                        connection.ensure_connection()
                    except OperationalError:
                        print(
                            "Cart reminder: DB connection lost, waiting to reconnect..."
                        )
                        if not wait_for_db():
                            time.sleep(21600)
                            continue

                    from email_utils.send_subscription_cart_reminder import (
                        check_and_send_cart_reminders,
                    )

                    reminders_sent = check_and_send_cart_reminders()

                    if reminders_sent > 0:
                        print(
                            f"Cart reminder: Sent {reminders_sent} reminder emails automatically"
                        )

                    # Close the connection so it isn't held stale during the long sleep
                    connection.close()

                except Exception as e:
                    print(f"Cart reminder error: {str(e)}")

                time.sleep(21600)

        thread = threading.Thread(target=cart_reminder_worker, daemon=True)
        thread.start()

        print("Cart reminder checker started - will run every 6 hours")
