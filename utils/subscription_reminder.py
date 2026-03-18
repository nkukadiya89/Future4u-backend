import logging

from django.utils import timezone

from company.models import Company
from email_utils.send_subscription_reminder import send_subscription_reminder_email
from subscription.models import PaymentSubscriptionItem

logger = logging.getLogger(__name__)


def send_subscription_reminders():
    try:
        today = timezone.now().date()

        companies_with_ending_subscriptions = (
            PaymentSubscriptionItem.objects.filter(
                payment_subscription__payment_status="paid",
                payment_subscription__active="Active",
                end_date__isnull=False,
            )
            .select_related("payment_subscription__company")
            .distinct()
        )

        sent_count = 0

        for subscription_item in companies_with_ending_subscriptions:
            company = subscription_item.payment_subscription.company

            # Calculate days until subscription ends
            days_until_end = (subscription_item.end_date - today).days

            # Send reminders for subscriptions ending in 5, 4, 3, and 2 days
            if days_until_end in [5, 4, 3, 2]:
                try:
                    # Send reminder email
                    success = send_subscription_reminder_email(
                        company=company, subscription_item=subscription_item, days_until_end=days_until_end
                    )

                    if success:
                        sent_count += 1
                        logger.info(f"Renewal reminder sent to {company.name} (Ends in {days_until_end} days)")
                    else:
                        logger.warning(
                            f"Failed to send renewal reminder to {company.name} (Ends in {days_until_end} days)"
                        )

                except Exception as e:
                    logger.error(f"Error sending renewal reminder to {company.name}: {str(e)}")

        logger.info(f"Total renewal reminder emails sent: {sent_count}")
        return {
            "success": True,
            "sent_count": sent_count,
            "total_companies": companies_with_ending_subscriptions.count(),
        }

    except Exception as e:
        logger.error(f"Error in send_subscription_reminders: {str(e)}")
        return {"success": False, "error": str(e), "sent_count": 0}


def get_companies_needing_reminders():
    """
    Get list of companies that need subscription renewal reminders
    Returns companies with days until subscription ends
    """
    try:
        today = timezone.now().date()

        companies_data = []

        companies_with_subscriptions = (
            PaymentSubscriptionItem.objects.filter(
                payment_subscription__payment_status="paid",
                payment_subscription__active="Active",
                end_date__isnull=False,
            )
            .select_related("payment_subscription__company")
            .distinct()
        )

        for subscription_item in companies_with_subscriptions:
            company = subscription_item.payment_subscription.company
            days_until_end = (subscription_item.end_date - today).days

            if days_until_end in [5, 4, 3, 2]:
                companies_data.append(
                    {
                        "company": company,
                        "subscription_item": subscription_item,
                        "days_until_end": days_until_end,
                        "needs_reminder_today": True,
                        "end_date": subscription_item.end_date,
                    }
                )
            elif days_until_end > 5:
                companies_data.append(
                    {
                        "company": company,
                        "subscription_item": subscription_item,
                        "days_until_end": days_until_end,
                        "needs_reminder_today": False,
                        "next_reminder_day": 5,
                        "end_date": subscription_item.end_date,
                    }
                )
            elif days_until_end <= 0:
                companies_data.append(
                    {
                        "company": company,
                        "subscription_item": subscription_item,
                        "days_until_end": days_until_end,
                        "needs_reminder_today": False,
                        "subscription_expired": True,
                        "end_date": subscription_item.end_date,
                    }
                )

        return companies_data

    except Exception as e:
        logger.error(f"Error in get_companies_needing_reminders: {str(e)}")
        return []


def send_manual_reminder(company_id, subscription_item_id=None):
    """
    Send a manual renewal reminder to a specific company
    """
    try:
        company = Company.objects.get(id=company_id)

        if subscription_item_id:
            subscription_item = PaymentSubscriptionItem.objects.get(id=subscription_item_id)
            today = timezone.now().date()
            days_until_end = (subscription_item.end_date - today).days
        else:
            # Find the most recent subscription item for this company
            subscription_item = PaymentSubscriptionItem.objects.filter(
                payment_subscription__company=company,
                payment_subscription__payment_status="paid",
                payment_subscription__active="Active",
                end_date__isnull=False,
            ).first()

            if not subscription_item:
                return {"success": False, "message": "No active subscription found for this company"}

            today = timezone.now().date()
            days_until_end = (subscription_item.end_date - today).days

        success = send_subscription_reminder_email(
            company=company, subscription_item=subscription_item, days_until_end=days_until_end
        )

        if success:
            logger.info(f"Manual renewal reminder sent to {company.name} (Ends in {days_until_end} days)")
            return {"success": True, "message": f"Renewal reminder sent to {company.name}"}
        else:
            return {"success": False, "message": f"Failed to send renewal reminder to {company.name}"}

    except Company.DoesNotExist:
        return {"success": False, "message": "Company not found"}
    except Exception as e:
        logger.error(f"Error in send_manual_reminder: {str(e)}")
        return {"success": False, "message": str(e)}
