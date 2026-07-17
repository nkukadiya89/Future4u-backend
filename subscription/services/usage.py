from django.db import transaction
from django.db.models import F

from subscription.models import FeatureUsage, SubscriptionFeature, UserSubscription


def apply_portal_limit(user, queryset, feature_code):
    """
    Slice a portal queryset (courses / internships / jobs) based on the
    user's active subscription plan limit.

    - Full access (is_unlimited=True) → no limit applied.
    - Limited access → only first N items are returned.
    - No active subscription or no feature config → queryset unchanged.

    Usage in get_queryset():
        base = apply_portal_limit(user, base, "course")
        return base
    """
    if user.user_type not in ["student", "parent", "working_professional"]:
        return queryset

    user_sub = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan_price__plan")
        .first()
    )
    if not user_sub:
        return queryset

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        return queryset

    feature = SubscriptionFeature.objects.filter(
        subscription=plan,
        feature_code=feature_code,
        is_enabled=True,
        deleted=False,
    ).first()
    if feature and not feature.is_unlimited:
        try:
            limit = int(feature.value or 0)
            return queryset[:limit]
        except (TypeError, ValueError):
            pass

    return queryset


def consume_feature(user, feature_code, quantity=1):
    """
    Validate and consume a feature usage.
    Raises Exception if limit exceeded.
    """

    # 1. Get active subscription
    user_sub = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan_price__plan")
        .first()
    )

    if not user_sub:
        raise Exception("No active subscription")

    plan_price = user_sub.plan_price
    subscription = getattr(plan_price, "plan", None)

    # 2. Get feature config
    feature = SubscriptionFeature.objects.filter(
        subscription=subscription,
        feature_code=feature_code,
        is_enabled=True,
        deleted=False,
    ).first()

    if not feature:
        raise Exception("Feature not available in plan")

    # 3. Unlimited case
    if feature.is_unlimited:
        return True

    limit = int(feature.value or 0)

    # 4. Atomic check + increment

    with transaction.atomic():
        usage, _ = FeatureUsage.objects.select_for_update().get_or_create(
            user=user, feature_code=feature_code, plan_price=plan_price, defaults={"used": 0}
        )

        if usage.used + quantity > limit:
            raise Exception("Usage limit exceeded")

        usage.used = F("used") + quantity
        usage.save(update_fields=["used"])

    return True
