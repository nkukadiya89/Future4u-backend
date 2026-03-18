"""
Cart Reminder Startup Checker
This module checks for existing cart items that need reminders when server starts
"""

import logging
from datetime import timedelta

from django.utils.timezone import now
from email_utils.send_subscription_cart_reminder import check_and_send_cart_reminders

logger = logging.getLogger(__name__)


def check_existing_cart_reminders():
    """
    Check for cart items that are already older than 24 hours when server starts
    This ensures no reminders are missed during server downtime
    """
    try:
        print("🔄 Checking for existing cart items needing reminders...")
        
        # Check and send any pending reminders
        reminders_sent = check_and_send_cart_reminders()
        
        if reminders_sent > 0:
            print(f"✅ Sent {reminders_sent} cart reminder emails on startup")
        else:
            print("✅ No pending cart reminders found on startup")
            
        return reminders_sent
        
    except Exception as e:
        print(f"❌ Error checking existing cart reminders: {str(e)}")
        logger.error(f"Error in check_existing_cart_reminders: {str(e)}")
        return 0
