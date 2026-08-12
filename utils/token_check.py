from django.db import transaction
from django.db.models import F
from django.utils.timezone import now

from activity_log.services import log_event
from subscription.constants import FEATURE_FIELD_MAP
from subscription.models import FeatureUsage, SubscriptionFeature, UserSubscription
from user.models import User
from user_profile.models import DEFAULT_ORG_TOKEN_LIMITS, OrganizationTokenUsage

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
    "project_gen": "Project Recommendations",
    "monthly_tokens": "Monthly Token Allowance",
}

MIN_TOKENS_REQUIRED = {
    "ai_chat": 600,
    "recommendation": 3000,
    "course_gen": 2000,
    "internship_gen": 2000,
    "job_gen": 2000,
    "resume_enhance": 500,
    "project_gen": 2000,
}

ORGANIZATION_TYPES = (
    User.Role.SCHOOL_COLLEGE,
    User.Role.INSTITUTE,
    User.Role.CORPORATE,
)


def _get_org_profile(user):
    if user.user_type == User.Role.SCHOOL_COLLEGE:
        return getattr(user, "school_college_profile", None)
    elif user.user_type == User.Role.INSTITUTE:
        return getattr(user, "institute_profile", None)
    elif user.user_type == User.Role.CORPORATE:
        return getattr(user, "corporate_profile", None)
    return None


def _resolve_token_owner(user):
    """Return the user whose token pool is charged for an org request.
    Staff own no quota — their usage is charged to the org owner who
    created them; all other users charge their own pool."""
    owner = user.get_owner_user()
    if owner is None or owner.deleted or not owner.is_active:
        raise Exception("Organization tokens unavailable. Contact your administrator.")
    return owner


class OrganizationTokenChargeError(Exception):
    pass


def _is_org_staff_profile(profile):
    """Return True when the profile belongs to an organization staff user."""
    return bool(getattr(getattr(profile, "user", None), "is_org_staff", False))


def _org_base_token_limit(profile, user_type):
    """Monthly base token allowance for an org profile.
    Staff always get 0 — they never auto-receive the org default."""
    if _is_org_staff_profile(profile):
        return 0
    return DEFAULT_ORG_TOKEN_LIMITS.get(
        user_type, DEFAULT_ORG_TOKEN_LIMITS[User.Role.INSTITUTE]
    )


def _check_org_monthly_reset(profile, user_type):
    """Reset token_limit to base default only.
    extra_token_limit is a one-time per-month grant — it resets to 0
    so the new month starts cleanly with just the config default.
    Staff users reset to 0 (their base is always 0)."""
    today = now().date()
    if not profile.last_token_reset_at:
        # Profile has not entered a reset cycle yet: start the clock
        # without touching the balance so pre-first-use top-ups survive.
        profile.last_token_reset_at = today
        profile.save(update_fields=["last_token_reset_at"])
        return
    if (today - profile.last_token_reset_at).days >= 30:
        base = _org_base_token_limit(profile, user_type)
        before_token = profile.token_limit
        before_extra = profile.extra_token_limit
        profile.token_limit = base
        profile.extra_token_limit = 0
        profile.last_token_reset_at = today
        profile.save(
            update_fields=["token_limit", "extra_token_limit", "last_token_reset_at"]
        )
        log_event(
            event="user.tokens_reset",
            description=(
                f"Monthly token reset for "
                f"{getattr(profile.user, 'email', profile.user_id)}"
            ),
            user=profile.user,
            entity_type="user",
            entity_id=profile.user_id,
            metadata={
                "base": base,
                "token_limit_before": before_token,
                "token_limit_after": base,
                "extra_token_before": before_extra,
                "extra_token_after": 0,
            },
        )


def adjust_extra_tokens(profile, new_extra_tokens, actor, *, request=None):
    with transaction.atomic():
        locked = type(profile).objects.select_for_update().get(id=profile.id)
        _check_org_monthly_reset(locked, locked.user.user_type)

        old = locked.extra_token_limit or 0
        before_token = locked.token_limit or 0
        increase = new_extra_tokens - old

        locked.extra_token_limit = new_extra_tokens
        if increase > 0:
            locked.token_limit = (locked.token_limit or 0) + increase
        locked.save(update_fields=["extra_token_limit", "token_limit"])

        profile.extra_token_limit = locked.extra_token_limit
        profile.token_limit = locked.token_limit
        profile.last_token_reset_at = locked.last_token_reset_at

        log_event(
            event="user.tokens_updated",
            description=(
                f"Set extra tokens to {new_extra_tokens} for " f"{locked.user.email}"
            ),
            user=actor,
            entity_type="user",
            entity_id=locked.user_id,
            metadata={
                "previous_extra": old,
                "new_extra": new_extra_tokens,
                "token_increase": increase,
                "token_limit_before": before_token,
                "token_limit_after": locked.token_limit,
            },
            request=request,
        )
    return locked


def _reset_subscription_monthly_tokens(user, user_sub):
    """Reset monthly token usage for subscription users if 30+ days have passed.
    Uses last_reset_at on UserSubscription. Also resets all feature-specific usage
    counts (assessment, ai_chat, etc.) so they get a fresh allowance each month."""
    today = now().date()
    if not user_sub.last_reset_at or (today - user_sub.last_reset_at).days >= 30:
        plan_price = user_sub.plan_price
        FeatureUsage.objects.filter(
            user=user,
            feature_code="monthly_tokens",
            plan_price=plan_price,
        ).update(used=0)
        FeatureUsage.objects.filter(
            user=user,
            plan_price=plan_price,
        ).exclude(
            feature_code="monthly_tokens"
        ).update(used=0)
        UserSubscription.objects.filter(id=user_sub.id).update(last_reset_at=today)


def check_token_available(user, feature_code, quantity=1):
    if user.is_superuser:
        return True

    name = FEATURE_NAMES.get(feature_code, feature_code)

    # Org users: availability check only, no deduction
    if user.user_type in ORGANIZATION_TYPES:
        owner = _resolve_token_owner(user)
        profile = _get_org_profile(owner)
        if not profile:
            raise Exception("Profile not found")

        with transaction.atomic():
            locked_profile = (
                type(profile).objects.select_for_update().get(id=profile.id)
            )
            _check_org_monthly_reset(locked_profile, owner.user_type)
            token_limit = locked_profile.token_limit

        min_required = MIN_TOKENS_REQUIRED.get(feature_code)
        if min_required is not None and token_limit < min_required:
            raise Exception(
                f"Insufficient tokens. Need at least {min_required} tokens "
                f"for {name}. Contact your super admin."
            )
        return True

    # Subscription users (existing flow unchanged)
    user_sub = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan_price__plan")
        .first()
    )

    if not user_sub:
        raise Exception("No active subscription. Please subscribe to a plan.")

    if user_sub.end_date < now().date():
        raise Exception("Your subscription has expired. Please renew your plan.")

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        raise Exception("No active subscription plan found.")

    _reset_subscription_monthly_tokens(user, user_sub)

    # Verify the feature is in the plan before token checks.
    if feature_code not in ("monthly_tokens", "recommendation"):
        field_name = FEATURE_FIELD_MAP.get(feature_code)
        if field_name:
            value = getattr(plan, field_name, 0)
            if isinstance(value, bool):
                if not value:
                    raise Exception(
                        f"{name} is not included in your current plan. "
                        f"Please upgrade to access this feature."
                    )
            elif isinstance(value, int):
                if value <= 0:
                    raise Exception(
                        f"{name} is not included in your current plan. "
                        f"Please upgrade to access this feature."
                    )
        else:
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

    # Token checks apply only to LLM-consuming features (in MIN_TOKENS_REQUIRED).
    min_required = MIN_TOKENS_REQUIRED.get(feature_code)
    if min_required is not None:
        base_limit = plan.no_of_tokens or 0
        if base_limit <= 0:
            raise Exception(
                "Monthly tokens are not included in your current plan. "
                "Please upgrade your plan to continue."
            )

        usage = FeatureUsage.objects.filter(
            user=user,
            feature_code="monthly_tokens",
            plan_price=user_sub.plan_price,
        ).first()
        used = usage.used if usage else 0

        if used + min_required > base_limit:
            raise Exception(
                f"You have used {used} out of {base_limit} monthly tokens. "
                f"At least {min_required} tokens are needed for {name}. "
                f"Please upgrade your plan or wait for your tokens to reset."
            )

    return True


def get_org_token_usage(profile, user_type):
    """Compute token usage stats for an org profile.

    Single source of truth. Returns monthly_limit, used_tokens,
    remaining_tokens, and usage_percentage.
    """
    base = _org_base_token_limit(profile, user_type)
    extra = profile.extra_token_limit or 0
    monthly_limit = base + extra
    remaining_tokens = profile.token_limit or 0
    used_tokens = max(monthly_limit - remaining_tokens, 0)
    usage_percentage = (
        round((used_tokens / monthly_limit) * 100, 1) if monthly_limit > 0 else 0
    )
    return {
        "monthly_limit": monthly_limit,
        "used_tokens": used_tokens,
        "remaining_tokens": remaining_tokens,
        "usage_percentage": usage_percentage,
    }


def charge_ai_usage(user, feature_code, actual_tokens):
    if user.is_superuser or actual_tokens <= 0:
        return 0
    if user.user_type not in ORGANIZATION_TYPES:
        return 0

    try:
        owner = _resolve_token_owner(user)
        profile = _get_org_profile(owner)
        if not profile:
            return 0

        with transaction.atomic():
            locked_profile = (
                type(profile).objects.select_for_update().get(id=profile.id)
            )
            _check_org_monthly_reset(locked_profile, owner.user_type)

            before = locked_profile.token_limit or 0
            deduction = min(actual_tokens, before)
            balance_after = before - deduction

            type(profile).objects.filter(id=locked_profile.id).update(
                token_limit=F("token_limit") - deduction
            )
            OrganizationTokenUsage.objects.create(
                organization_id=owner.id,
                user=user,
                feature_code=feature_code,
                tokens_used=deduction,
                balance_after=balance_after,
            )
            return deduction
    except Exception as exc:
        raise OrganizationTokenChargeError(
            f"Failed to charge organization token pool for {feature_code}"
        ) from exc


def deduct_monthly_tokens(user, actual_tokens, feature_code=None, request=None):
    """Deduct actual LLM token usage after a successful AI generation.
    Staff are charged to their owning org's pool; deduction and its
    audit event share one transaction."""
    if user.is_superuser or actual_tokens <= 0:
        return

    # Org users: deduct from the owner's profile token pool
    if user.user_type in ORGANIZATION_TYPES:
        owner = _resolve_token_owner(user)
        profile = _get_org_profile(owner)
        if not profile:
            return

        with transaction.atomic():
            locked_profile = (
                type(profile).objects.select_for_update().get(id=profile.id)
            )
            _check_org_monthly_reset(locked_profile, owner.user_type)

            deduction = min(actual_tokens, locked_profile.token_limit)
            before = locked_profile.token_limit or 0
            type(profile).objects.filter(id=locked_profile.id).update(
                token_limit=F("token_limit") - deduction
            )
            if deduction > 0:
                log_event(
                    event="user.tokens_deducted",
                    description=(
                        f"Deducted {deduction} tokens for "
                        f"{feature_code or 'AI feature'}"
                    ),
                    user=user,
                    entity_type="user",
                    entity_id=owner.id,
                    metadata={
                        "feature_code": feature_code,
                        "tokens": deduction,
                        "owner_user_id": owner.id,
                        "owner_profile_id": profile.id,
                        "before": before,
                        "after": before - deduction,
                    },
                    request=request,
                )
        return

    # Subscription users (existing flow unchanged)
    user_sub = (
        UserSubscription.objects.filter(user=user, is_active=True)
        .select_related("plan_price__plan")
        .first()
    )

    if not user_sub:
        return

    plan = getattr(user_sub.plan_price, "plan", None)
    if not plan:
        return

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
