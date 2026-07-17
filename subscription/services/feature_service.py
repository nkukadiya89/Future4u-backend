from subscription.models import SubscriptionFeature


class FeatureService:
    """Handles creation and update of SubscriptionFeature records."""

    # Flat-field toggle features (is_core=True)
    TOGGLE_FIELDS = [
        ("career_compare", "career_compare", "Career Compare"),
        ("career_roadmap", "career_roadmap", "Career Roadmap Path"),
        ("ai_chat_access", "ai_chat", "AI Chat Access"),
    ]

    # Count-based features (is_hidden=True)
    COUNT_FIELDS = [
        ("no_of_profile_assessment", "assessment", "Profile Assessments"),
        ("no_of_tokens", "monthly_tokens", "Monthly Token Allowance"),
    ]

    # Access-type features (is_hidden=True)
    ACCESS_PAIRS = [
        ("internship_access_type", "no_of_internship_access", "internship"),
        ("job_portal_access_type", "no_of_job_portal_access", "job"),
        ("course_portal_access_type", "no_of_course_portal_access", "course"),
        ("project_topic_access_type", "no_of_project_topic_access", "project_topic"),
    ]

    # Core feature name → (feature_code, display_name) mapping
    CORE_FEATURE_MAP = {
        "career compare": ("career_compare", "Career Compare"),
        "career roadmap path": ("career_roadmap", "Career Roadmap Path"),
        "ai chat access": ("ai_chat", "AI Chat Access"),
    }

    @staticmethod
    def upsert(subscription, feature_code, *, feature_name=None,
               is_enabled=None, value=None, is_unlimited=None,
               is_core=False, is_hidden=False, user=None):
        """Create or update a SubscriptionFeature.

        If feature_code is provided, tries to find + update existing record.
        If feature_code is None or no existing record found, creates a new one.
        """
        if feature_code:
            existing = SubscriptionFeature.objects.filter(
                subscription=subscription,
                feature_code=feature_code,
                deleted=False,
            ).first()

            if existing:
                if feature_name is not None:
                    existing.feature_name = feature_name
                if is_enabled is not None:
                    existing.is_enabled = is_enabled
                if value is not None:
                    existing.value = str(value)
                if is_unlimited is not None:
                    existing.is_unlimited = is_unlimited
                existing.is_core = is_core
                existing.is_hidden = is_hidden
                existing.updated_by = user
                existing.save()
                return

        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_code=feature_code,
            feature_name=feature_name or "",
            is_enabled=bool(is_enabled) if is_enabled is not None else True,
            value=str(value) if value is not None else None,
            is_unlimited=bool(is_unlimited) if is_unlimited is not None else False,
            is_core=is_core,
            is_hidden=is_hidden,
            created_by=user,
        )

    @classmethod
    def sync_flat_fields(cls, subscription, data, user):
        """Process count, access, and toggle flat fields from validated_data."""
        # Count fields (hidden, numeric value)
        for field, code, name in cls.COUNT_FIELDS:
            if field in data:
                cls.upsert(
                    subscription, code,
                    feature_name=name, value=data[field],
                    is_hidden=True, user=user,
                )

        # Access-type fields (hidden, unlimited flag + optional count)
        for type_field, count_field, code in cls.ACCESS_PAIRS:
            if type_field in data or count_field in data:
                kwargs = {"is_hidden": True, "user": user}
                if type_field in data:
                    kwargs["is_unlimited"] = (data[type_field] == "full")
                if count_field in data:
                    kwargs["value"] = data[count_field]
                access_name = code.replace("_", " ").title() + " Access"
                cls.upsert(
                    subscription, code,
                    feature_name=access_name, **kwargs
                )

        # Toggle fields (core, boolean)
        for field, code, name in cls.TOGGLE_FIELDS:
            if field in data:
                cls.upsert(
                    subscription, code,
                    feature_name=name, is_enabled=bool(data[field]),
                    is_core=True, user=user,
                )

    @classmethod
    def sync_core_features(cls, subscription, core_data, user):
        """Process core_feature array from validated_data."""
        if core_data is None:
            return
        for item in core_data:
            name = (item.get("feature_name") or "").strip().lower()
            enabled = bool(
                item.get("feature_status", item.get("is_enabled", True))
            )
            match = cls.CORE_FEATURE_MAP.get(name)
            if match:
                code, display_name = match
                cls.upsert(
                    subscription, code,
                    feature_name=display_name,
                    is_enabled=enabled,
                    is_core=True,
                    user=user,
                )

    @classmethod
    def sync_custom_features(cls, subscription, custom_features_data, user, *, mode="create"):
        """Process subscription_feature (non-core, user-defined) array.

        In 'create' mode: always create new feature records.
        In 'update' mode: update existing by feature_name match, create new if missing.
        """
        if custom_features_data is None:
            return

        if mode == "update":
            existing_features = SubscriptionFeature.objects.filter(
                subscription=subscription,
                is_core=False,
                is_hidden=False,
                deleted=False,
            )
            existing_by_name = {
                (f.feature_name or "").strip().lower(): f
                for f in existing_features
            }

        for f in custom_features_data:
            name = f.get("feature_name") or f.get("feature", "")
            enabled = bool(
                f.get("feature_status", f.get("is_enabled", True))
            )

            if mode == "update":
                key = name.strip().lower()
                existing = existing_by_name.get(key)
                if existing:
                    existing.is_enabled = enabled
                    existing.updated_by = user
                    existing.save()
                    continue

            cls.upsert(
                subscription, None,
                feature_name=name, is_enabled=enabled,
                is_core=False, user=user,
            )
