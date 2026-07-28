from subscription.models import SubscriptionFeature


class FeatureService:
    """Handles creation and update of SubscriptionFeature records."""

    @staticmethod
    def upsert(
        subscription, feature_code, *, feature_name=None, is_enabled=None, user=None
    ):
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
                existing.updated_by = user
                existing.save()
                return

        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_code=feature_code,
            feature_name=feature_name or "",
            is_enabled=bool(is_enabled) if is_enabled is not None else True,
            created_by=user,
        )

    @classmethod
    def sync_custom_features(cls, subscription, custom_features_data, user):
        if not custom_features_data:
            return

        existing_features = SubscriptionFeature.objects.filter(
            subscription=subscription,
            deleted=False,
        )
        existing_by_name = {
            (f.feature_name or "").strip().lower(): f for f in existing_features
        }

        for f in custom_features_data:
            name = f.get("feature_name") or f.get("feature", "")
            enabled = bool(f.get("feature_status", f.get("is_enabled", True)))

            key = name.strip().lower()
            existing = existing_by_name.get(key)
            if existing:
                existing.is_enabled = enabled
                existing.updated_by = user
                existing.save()
                continue

            cls.upsert(
                subscription,
                None,
                feature_name=name,
                is_enabled=enabled,
                user=user,
            )
