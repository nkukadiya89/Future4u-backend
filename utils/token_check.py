
from django.db import transaction
from django.db.models import F
from django.utils.timezone import now

from subscription.models import FeatureUsage, SubscriptionFeature, UserSubscription
from subscription.services.usage import consume_feature
from token_override.models import TokenOverride


def get_bonus_tokens(user):
    """Get total bonus monthly tokens from admin overrides (per-user + entity-level)."""
    total_bonus = 0

    # Direct per-user override
    direct = TokenOverride.objects.filter(
        user=user,
        is_active=True,
        deleted=False,
    ).first()
    if direct:
        total_bonus += direct.extra_monthly_tokens

    # Entity-level override: check if user belongs to a school/college/institute/corporate
    # via their StudentProfile.referred_by or ProfessionalProfile.referred_by
    referred_by_user_id = None
    if hasattr(user, "student_profile") and user.student_profile:
        referred_by_user_id = user.student_profile.referred_by_id
    elif hasattr(user, "professional_profile") and user.professional_profile:
        referred_by_user_id = user.professional_profile.referred_by_id

    if referred_by_user_id:
        entity_bonus = TokenOverride.objects.filter(
            entity_user_id=referred_by_user_id,
            is_active=True,
            deleted=False,
        ).first()
        if entity_bonus:
            total_bonus += entity_bonus.extra_monthly_tokens

    return total_bonus


def check_and_deduct_token(user, feature_code, quantity=1):

    # 1. Look up subscription + monthly token config
    user_sub = UserSubscription.objects.filter(
        user=user, is_active=True
    ).select_related("plan_price__plan").first()

    if not user_sub:
        raise Exception("No active subscription. Please subscribe to a plan.")

    # Check if subscription period has expired
    if user_sub.end_date < now().date():
        raise Exception(
            "Your subscription has expired. Please renew your plan."
        )

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        raise Exception("No active subscription plan found.")

    monthly_feature = SubscriptionFeature.objects.filter(
        subscription=plan,
        feature_code="monthly_tokens",
        is_enabled=True,
        deleted=False,
    ).first()

    if not monthly_feature:
        raise Exception("Monthly tokens not available in your plan.")

    # 2. Deduct monthly_tokens AND per-feature in a SINGLE atomic transaction
    #    so that if either fails, BOTH roll back together.
    #    consume_feature() has its own nested atomic (savepoint); if it fails,
    #    the outer atomic rolls back the monthly_tokens deduction too.
    with transaction.atomic():
        if not monthly_feature.is_unlimited:
            base_limit = int(monthly_feature.value or 0)
            bonus = get_bonus_tokens(user)
            effective_limit = base_limit + bonus

            usage, _ = FeatureUsage.objects.select_for_update().get_or_create(
                user=user,
                feature_code="monthly_tokens",
                plan_price=user_sub.plan_price,
                defaults={"used": 0},
            )
            if usage.used + quantity > effective_limit:
                raise Exception(
                    "Monthly token limit exceeded. "
                    "Please upgrade your plan or contact support."
                )
            usage.used = F("used") + quantity
            usage.save(update_fields=["used"])

        # Deduct from specific feature (e.g. job_gen, course_gen)
        # If consume_feature raises, we catch and re-raise so the outer
        # atomic rolls back the monthly_tokens deduction too.
        try:
            consume_feature(user, feature_code, quantity)
        except Exception as e:
            error_msg = str(e).lower()
            if "not available in plan" in error_msg:
                raise Exception(
                    f"{feature_code} is not included in your plan."
                )
            if "no active subscription" in error_msg:
                raise Exception(
                    "Your subscription is no longer active. "
                    "Please renew your plan."
                )
            raise Exception(f"Your {feature_code} limit is exhausted.")

    return True
