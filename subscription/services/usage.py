from django.db import transaction
from django.db.models import F

from subscription.models import FeatureUsage, SubscriptionFeature, UserSubscription

_PORTAL_FIELD_MAP = {
    "internship": ("internship_access_type", "no_of_internship_access"),
    "job": ("job_portal_access_type", "no_of_job_portal_access"),
    "course": ("course_portal_access_type", "no_of_course_portal_access"),
    "project_topic": ("project_topic_access_type", "no_of_project_topic_access"),
}

_CONSUME_FIELD_MAP = {
    "assessment": "no_of_profile_assessment",
    "monthly_tokens": "no_of_tokens",
    "internship": "no_of_internship_access",
    "job": "no_of_job_portal_access",
    "course": "no_of_course_portal_access",
    "project_topic": "no_of_project_topic_access",
}


def apply_portal_limit(user, queryset, feature_code):
    """
    Slice a portal queryset (courses / internships / jobs) based on the
    user's active subscription plan limit.

    - Full access → no limit applied.
    - Limited access → only first N items are returned.
    - No active subscription or no feature config → queryset unchanged.
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

    mapping = _PORTAL_FIELD_MAP.get(feature_code)
    if not mapping:
        return queryset

    access_field, count_field = mapping
    access_type = getattr(plan, access_field, "full")

    if access_type == "limited":
        limit = getattr(plan, count_field, None) or 0
        if limit > 0:
            return queryset[:limit]

    return queryset


def consume_feature(user, feature_code, quantity=1):
    """
    Validate and consume a feature usage.
    Raises Exception if limit exceeded.
    """
    user_sub = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan_price__plan")
        .first()
    )

    if not user_sub:
        raise Exception("No active subscription")

    plan_price = user_sub.plan_price
    subscription = getattr(plan_price, "plan", None)

    count_field = _CONSUME_FIELD_MAP.get(feature_code)
    if count_field:
        access_field = {
            "internship": "internship_access_type",
            "job": "job_portal_access_type",
            "course": "course_portal_access_type",
            "project_topic": "project_topic_access_type",
        }.get(feature_code)

        if access_field:
            access_type = getattr(subscription, access_field, "full")
            if access_type == "full":
                return True

        limit = getattr(subscription, count_field, 0) or 0
        if limit <= 0:
            raise Exception("Feature not available in plan")
    else:
        feature = SubscriptionFeature.objects.filter(
            subscription=subscription,
            feature_code=feature_code,
            is_enabled=True,
            deleted=False,
        ).first()
        if not feature:
            raise Exception("Feature not available in plan")
        return True

    with transaction.atomic():
        usage, _ = FeatureUsage.objects.select_for_update().get_or_create(
            user=user, feature_code=feature_code, plan_price=plan_price, defaults={"used": 0}
        )

        if usage.used + quantity > limit:
            raise Exception("Usage limit exceeded")

        usage.used = F("used") + quantity
        usage.save(update_fields=["used"])

    return True
