from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from subscription.models import Subscription, UserSubscription


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def assign_free_subscription(sender, instance, created, **kwargs):
    """
    Auto-assign the "Free" plan to new users on signup.

    Only applies to subscription-based user types:
    student, parent, and working_professional.

    If no "Free" plan exists, the signal does nothing (user gets no plan).
    """
    if not created:
        return

    # Only assign to subscription-based user types
    if instance.user_type not in [
        "student",
        "parent",
        "working_professional",
    ]:
        return

    try:
        free_plan = (
            Subscription.objects.filter(
                package_name__iexact="Free", is_active=True, deleted=False
            )
            .order_by("-id")
            .first()
        )

        if not free_plan:
            return

        plan_price = (
            free_plan.prices.filter(is_active=True, deleted=False)
            .order_by("-price")
            .first()
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
        # Silently skip on error to not block user creation
        pass
