import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from utils.email_logger import log_email_failed, log_email_sent

logger = logging.getLogger(__name__)


def send_subscription_reminder_email(company, subscription_item=None, days_until_end=None, day=None):
    """
    Send subscription renewal reminder email to company
    days_until_end: Days until subscription ends (7, 3, 1)
    day: Legacy parameter for backward compatibility
    """
    try:
        # Get company admin user
        company_user = None
        from user.models import User

        company_users = User.objects.filter(company_id=company.id, is_active=True)

        if company_users.exists():
            company_user = company_users.first()

        if not company_user:
            logger.error(f"No active user found for company {company.name}")
            return False

        # Use days_until_end if provided, otherwise fall back to day
        reminder_days = days_until_end if days_until_end is not None else day

        if not reminder_days or reminder_days not in [5, 4, 3, 2]:
            logger.error(f"Invalid reminder days: {reminder_days}. Must be 5, 4, 3, or 2")
            return False

        # Prepare email context
        context = {
            "company_name": company.name,
            "person_name": company.person_name,
            "days_until_end": reminder_days,
            "company_user": company_user,
            "login_url": (
                f"{settings.FRONTEND_URL}/login"
                if hasattr(settings, "FRONTEND_URL")
                else "https://your-frontend-url.com/login"
            ),
            "pricing_url": (
                f"{settings.FRONTEND_URL}/pricing"
                if hasattr(settings, "FRONTEND_URL")
                else "https://your-frontend-url.com/pricing"
            ),
        }

        # Add subscription details if available
        if subscription_item:
            context.update(
                {
                    "subscription_package": subscription_item.subscription.package_name,
                    "end_date": subscription_item.end_date,
                    "subscription_amount": subscription_item.plan_total,
                }
            )

        # Choose template based on days until end
        if reminder_days == 5:
            subject = "Your OutdoorX Subscription Ends in 5 Days - Renewal Reminder"
            template_name = "subscription_reminder_day5.html"
        elif reminder_days == 4:
            subject = "Your OutdoorX Subscription Ends in 4 Days - Renewal Reminder"
            template_name = "subscription_reminder_day4.html"
        elif reminder_days == 3:
            subject = "Urgent: Your OutdoorX Subscription Ends in 3 Days - Renew Now"
            template_name = "subscription_reminder_day3.html"
        elif reminder_days == 2:
            subject = "Final Notice: Your OutdoorX Subscription Ends in 2 Days - Act Now"
            template_name = "subscription_reminder_day2.html"
        else:
            return False

        # Render email content
        html_content = render_to_string(f"subscription_reminders/{template_name}", context)
        text_content = strip_tags(html_content)

        # Create and send email
        email = EmailMultiAlternatives(
            subject=subject, body=text_content, from_email=settings.DEFAULT_FROM_EMAIL, to=[company_user.email]
        )
        email.attach_alternative(html_content, "text/html")

        try:
            email.send()
            # Log successful email
            log_email_sent(email, email_type="subscription_reminder", related_user=company_user)
            logger.info(
                f"Subscription renewal reminder email sent to {company.name} for {reminder_days} days until end"
            )
            return True
        except Exception as e:
            # Log failed email
            log_email_failed(
                company_user.email, subject, str(e), settings.DEFAULT_FROM_EMAIL, email_type="subscription_reminder"
            )
            logger.error(f"Error sending subscription renewal reminder to {company.name}: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error sending subscription renewal reminder to {company.name}: {str(e)}")
        return False
