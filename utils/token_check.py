
from django.db import transaction
from django.db.models import F
from django.utils.timezone import now

from subscription.models import FeatureUsage, SubscriptionFeature, UserSubscription
from user.models import User


FEATURE_NAMES = {
    "ai_chat": "AI Chat",
    "career_compare": "Career Compare",
    "career_roadmap": "Career Roadmap Path",
    "assessment": "Profile Assessment",
    "recommendation": "Career Recommendation",
    "course_gen": "Course Generation",
    "internship_gen": "Internship Generation",
    "job_gen": "Job Generation",
    "resume_enhance": "Resume Builder",
    "monthly_tokens": "Monthly Token Allowance",
}

MIN_TOKENS_REQUIRED = {
    "ai_chat": 500,
    "recommendation": 3000,
    "course_gen": 500,
    "internship_gen": 500,
    "job_gen": 500,
}

ORGANIZATION_TYPES = (
    User.Role.SCHOOL_COLLEGE,
    User.Role.INSTITUTE,
    User.Role.CORPORATE,
)

# Default monthly token allowance per org type (used during monthly reset).
# Stored in code so changing it affects ALL existing users, not just new ones.
# Per-user overrides are tracked via extra_token_limit on the profile.
DEFAULT_ORG_TOKEN_LIMITS = {
    User.Role.INSTITUTE: 20000,
    User.Role.CORPORATE: 20000,
    User.Role.SCHOOL_COLLEGE: 15000,
}


def _get_org_profile(user):
    if user.user_type == User.Role.SCHOOL_COLLEGE:
        return getattr(user, "school_college_profile", None)
    elif user.user_type == User.Role.INSTITUTE:
        return getattr(user, "institute_profile", None)
    elif user.user_type == User.Role.CORPORATE:
        return getattr(user, "corporate_profile", None)
    return None


def _check_org_monthly_reset(profile, user_type):
    """Reset token_limit to base default only.
    extra_token_limit is a one-time per-month grant — it resets to 0
    so the new month starts cleanly with just the config default."""
    today = now().date()
    if not profile.last_token_reset_at or (today - profile.last_token_reset_at).days >= 30:
        base = DEFAULT_ORG_TOKEN_LIMITS.get(user_type, 20000)
        profile.token_limit = base
        profile.extra_token_limit = 0
        profile.last_token_reset_at = today
        profile.save(update_fields=["token_limit", "extra_token_limit", "last_token_reset_at"])


def _reset_subscription_monthly_tokens(user, user_sub):
    """Reset monthly token usage for subscription users if 30+ days have passed.
    Uses last_reset_at on UserSubscription. Also resets all feature-specific usage
    counts (assessment, ai_chat, etc.) so they get a fresh allowance each month."""
    today = now().date()
    if not user_sub.last_reset_at or (today - user_sub.last_reset_at).days >= 30:
        plan_price = user_sub.plan_price
        # Reset monthly_tokens usage to 0
        FeatureUsage.objects.filter(
            user=user,
            feature_code="monthly_tokens",
            plan_price=plan_price,
        ).update(used=0)
        # Reset all feature-specific usage counts too
        FeatureUsage.objects.filter(
            user=user,
            plan_price=plan_price,
        ).exclude(feature_code="monthly_tokens").update(used=0)
        # Update reset timestamp
        UserSubscription.objects.filter(id=user_sub.id).update(last_reset_at=today)


def check_token_available(user, feature_code, quantity=1):
    if user.is_superuser:
        return True

    name = FEATURE_NAMES.get(feature_code, feature_code)

    # ── ORG USERS: CHECK availability only, no deduction ──
    if user.user_type in ORGANIZATION_TYPES:
        profile = _get_org_profile(user)
        if not profile:
            raise Exception("Profile not found")

        _check_org_monthly_reset(profile, user.user_type)

        min_required = MIN_TOKENS_REQUIRED.get(feature_code, 100)
        if profile.token_limit < min_required:
            raise Exception(
                f"Insufficient tokens. Need at least {min_required} tokens "
                f"for {name}. Contact your super admin."
            )
        return True

    # ── SUBSCRIPTION USERS (existing flow unchanged) ──
    user_sub = UserSubscription.objects.filter(
        user=user, is_active=True
    ).select_related("plan_price__plan").first()

    if not user_sub:
        raise Exception("No active subscription. Please subscribe to a plan.")

    if user_sub.end_date < now().date():
        raise Exception(
            "Your subscription has expired. Please renew your plan."
        )

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        raise Exception("No active subscription plan found.")

    # Check monthly reset before checking limits
    _reset_subscription_monthly_tokens(user, user_sub)

    monthly_feature = SubscriptionFeature.objects.filter(
        subscription=plan,
        feature_code="monthly_tokens",
        is_enabled=True,
        deleted=False,
    ).first()

    if not monthly_feature:
        raise Exception(
            "Monthly tokens are not included in your current plan. "
            "Please upgrade your plan to continue."
        )

    # Check monthly token budget — block if user has exhausted their allowance
    if not monthly_feature.is_unlimited:
        base_limit = int(monthly_feature.value or 0)
        if base_limit <= 0:
            raise Exception(
                "Your monthly token plan is not configured properly. "
                "Please contact support."
            )

        # Get how many tokens used this month
        usage = FeatureUsage.objects.filter(
            user=user,
            feature_code="monthly_tokens",
            plan_price=user_sub.plan_price,
        ).first()
        used = usage.used if usage else 0

        min_required = MIN_TOKENS_REQUIRED.get(feature_code, 100)
        if used + min_required > base_limit:
            raise Exception(
                f"You have used {used} out of {base_limit} monthly tokens. "
                f"At least {min_required} tokens are needed for {name}. "
                f"Please upgrade your plan or wait for your tokens to reset."
            )

    # Verify this specific feature is included in the user's plan
    # recommendation is bundled with assessment — no separate plan feature
    if feature_code not in ("monthly_tokens", "recommendation"):
        feature = SubscriptionFeature.objects.filter(
            subscription=plan,
            feature_code=feature_code,
            is_enabled=True,
            deleted=False,
        ).first()
        if not feature:
            raise Exception(
                f"{name} is not included in your current plan. "
                f"Please upgrade to access this feature."
            )

    return True


def deduct_monthly_tokens(user, actual_tokens):
    """Deduct actual LLM token usage after a successful AI generation."""
    if user.is_superuser or actual_tokens <= 0:
        return

    # ── ORG USERS: deduct from profile.token_limit ──
    if user.user_type in ORGANIZATION_TYPES:
        profile = _get_org_profile(user)
        if not profile:
            return

        _check_org_monthly_reset(profile, user.user_type)

        with transaction.atomic():
            locked_profile = type(profile).objects.select_for_update().get(id=profile.id)
            if locked_profile.token_limit < actual_tokens:
                raise Exception("Monthly token allowance exhausted.")
            type(profile).objects.filter(id=locked_profile.id).update(
                token_limit=F("token_limit") - actual_tokens
            )
        return

    # ── SUBSCRIPTION USERS (existing flow unchanged) ──
    user_sub = UserSubscription.objects.filter(
        user=user, is_active=True
    ).select_related("plan_price__plan").first()

    if not user_sub:
        return

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        return

    # Check monthly reset before deducting
    _reset_subscription_monthly_tokens(user, user_sub)

    with transaction.atomic():
        usage, _ = FeatureUsage.objects.select_for_update().get_or_create(
            user=user,
            feature_code="monthly_tokens",
            plan_price=user_sub.plan_price,
            defaults={"used": 0},
        )
        usage.used = F("used") + actual_tokens
        usage.save(update_fields=["used"])
