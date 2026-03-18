import threading
import time
from django.apps import AppConfig


class SubcriptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "subscription"

    def ready(self) -> None:
        self.check_startup_reminders()
        
        self.start_cart_reminder_checker()

    def check_startup_reminders(self):
        """Check for cart items that already need reminders on startup"""
        try:
            from utils.cart_reminder_checker import check_existing_cart_reminders
            
            check_existing_cart_reminders()
            
        except Exception as e:
            print(f"🛒 Startup check error: {str(e)}")

    def start_cart_reminder_checker(self):
        """Start background thread to check and send cart reminders every 6 hours"""
        
        def cart_reminder_worker():
            """Background worker that runs every 6 hours"""
            while True:
                try:
                    from email_utils.send_subscription_cart_reminder import check_and_send_cart_reminders
                    
                    reminders_sent = check_and_send_cart_reminders()
                    
                    if reminders_sent > 0:
                        print(f"🛒 Cart reminder: Sent {reminders_sent} reminder emails automatically")
                    
                except Exception as e:
                    print(f"🛒 Cart reminder error: {str(e)}")
                
                time.sleep(21600)
        
        thread = threading.Thread(target=cart_reminder_worker, daemon=True)
        thread.start()
        
        print("🛒 Cart reminder checker started - will run every 6 hours")