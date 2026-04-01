import logging
import os
from datetime import timedelta

from decouple import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now

from subscription.models import SubscriptionCart
from utils.email_logger import log_email_failed, log_email_sent
from user_profile.models import BusinessSetting

logger = logging.getLogger(__name__)


def send_subscription_cart_reminder_email(cart_items, company, user_email):
    from_email = settings.DEFAULT_FROM_EMAIL
    try:
        app_url = config('APP_URL')

        cart_data = []
        for item in cart_items:
            business_setting = BusinessSetting.objects.filter(company_id=company.id).first()
            is_gujarat = bool(
                business_setting and business_setting.state
                and business_setting.state.name.lower() == "gujarat"
            )
            if is_gujarat:
                sgst_rate = business_setting.sgst if business_setting else 9
                cgst_rate = business_setting.cgst if business_setting else 9
                igst_rate = None
            else:
                sgst_rate = None
                cgst_rate = business_setting.cgst if business_setting else 18
                igst_rate = business_setting.igst if business_setting else 18

            cart_data.append({
                'package_name': item.subscription.package_name,
                'quantity': item.quantity,
                'device_price': item.subscription.device_sell_price,
                'subscription_price': item.subscription.subscription_sell_price,
                'subscription_type': '1 year',
                'is_gujarat': is_gujarat,
                'cgst_rate': cgst_rate,
                'sgst_rate': sgst_rate,
                'igst_rate': igst_rate,
            })

        context = {
            'company_name': company.name,
            'person_name': company.name,
            'cart_items': cart_data,
            'cart_url': f"{app_url}cart-summary",
        }

        html_content = render_to_string('subscription-cart-reminder.html', context)
        text_content = strip_tags(html_content)
        subject = f"Complete Your Subscription Purchase - {company.name}"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[user_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        log_email_sent(
            email_obj=email,
            email_type="cart_reminder",
            related_company=company,
            sender_id=1,
        )
        logger.info(f"Subscription cart reminder email sent to {user_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send subscription cart reminder email to {user_email}: {str(e)}")
        log_email_failed(
            recipient_email=user_email,
            subject="Subscription Cart Reminder",
            error_message=str(e),
            sender_email=from_email,
            email_type="cart_reminder",
            related_company=company,
            sender_id=1,
        )
        return False


def check_and_send_cart_reminders():
    """
    Check for cart items older than 24 hours and send reminder emails
    This function should be called by a management command or scheduled task
    """
    try:
        # Find cart items that are:
        # 1. Not deleted
        # 2. Created more than 24 hours ago
        # 3. Haven't had a reminder sent in the last 24 hours (or never)
        cutoff_time = now() - timedelta(hours=24)
        
        # Get carts that need reminders - handle case where field might not exist
        try:
            carts_needing_reminder = SubscriptionCart.objects.filter(
                deleted=False,
                created_at__lt=cutoff_time,
            ).filter(
                Q(last_reminder_sent__lt=cutoff_time) | Q(last_reminder_sent__isnull=True)
            ).select_related('company', 'subscription')
        except Exception:
            carts_needing_reminder = SubscriptionCart.objects.filter(
                deleted=False,
                created_at__lt=cutoff_time,
            ).select_related('company', 'subscription')
        
        # Group by company to send one email per company
        companies_with_carts = {}
        for cart in carts_needing_reminder:
            if cart.company.id not in companies_with_carts:
                companies_with_carts[cart.company.id] = {
                    'company': cart.company,
                    'cart_items': [],
                    'user_email': None
                }
            companies_with_carts[cart.company.id]['cart_items'].append(cart)
        
        # Send reminders for each company
        reminders_sent = 0
        for company_id, data in companies_with_carts.items():
            company = data['company']
            cart_items = data['cart_items']
            
            # Get user email - try company email first, then look for users
            user_email = company.email if company.email else None
            
            if not user_email:
                # Get first user from this company
                from django.contrib.auth import get_user_model
                User = get_user_model()
                company_user = User.objects.filter(company_id=company.id).first()
                if company_user and company_user.email:
                    user_email = company_user.email
            
            if user_email:
                # Send reminder email
                success = send_subscription_cart_reminder_email(
                    cart_items=cart_items,
                    company=company,
                    user_email=user_email
                )
                
                if success:
                    # Update last_reminder_sent for all cart items
                    try:
                        SubscriptionCart.objects.filter(
                            id__in=[item.id for item in cart_items]
                        ).update(last_reminder_sent=now())
                    except Exception:
                        pass
                    
                    reminders_sent += 1
                    logger.info(f"Sent cart reminder to company {company.name} ({user_email})")
                else:
                    logger.error(f"Failed to send cart reminder to company {company.name}")
            else:
                logger.warning(f"No email address found for company {company.name}")
        
        logger.info(f"Cart reminder process completed. Sent {reminders_sent} reminders.")
        return reminders_sent
        
    except Exception as e:
        logger.error(f"Error in check_and_send_cart_reminders: {str(e)}")
        return 0
