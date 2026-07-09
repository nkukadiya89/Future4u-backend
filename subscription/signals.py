from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from subscription.models import Subscription, UserSubscription


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_basic_subscription(sender, instance, created, **kwargs):
    """Assign the 'Basic' subscription to a user on account creation.

    This looks for a Subscription with package_name 'Basic' (case-insensitive),
    active and not deleted. If found, creates a UserSubscription for the new user.
    """
    if not created:
        return

    try:
        basic = (
            Subscription.objects.filter(
                package_name__iexact="Basic", is_active=True, deleted=False
            )
            .order_by("-id")
            .first()
        )

        if not basic:
            return

        # create only if user doesn't already have an active subscription for this plan
        # pick default active PlanPrice for the Basic plan
        plan_price = (
            basic.prices.filter(is_active=True, deleted=False).order_by("-price").first()
        )
        if not plan_price:
            return

        UserSubscription.objects.get_or_create(
            user=instance,
            plan_price=plan_price,
            defaults={
                "start_date": now().date(),
                "end_date": now().date() + timedelta(days=plan_price.duration_days),
                "is_active": True,
            },
        )
    except Exception:
        # avoid breaking user creation; logging can be added if needed
        pass
