from rest_framework import serializers

from .models import (
    Discount,
    PaymentSubscription,
    PlanPrice,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
    UserSubscription,
)
from subscription.services.pricing import calculate_price


class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ["id", "feature_name", "is_core", "is_enabled"]


class SubscriptionSerializer(serializers.ModelSerializer):
    features = SubscriptionFeatureSerializer(many=True, read_only=True)
    prices = serializers.SerializerMethodField()

    def get_prices(self, obj):
        prices = obj.prices.filter(is_active=True, deleted=False)
        return [
            {
                "id": p.id,
                "period": p.period,
                "price": p.price,
                "duration_days": p.duration_days,
            }
            for p in prices
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Writable serializer that accepts frontend/admin payload and creates
    a Subscription (plan) plus a PlanPrice snapshot and SubscriptionFeatures.

    Accepts these write-only fields:
      - subscription_price / subscription_sell_price
      - duration_days
      - period (optional)
      - core_features (list of dicts)
      - subscription_features or subscription_feature (list of dicts)
    """

    subscription_price = serializers.IntegerField(write_only=True, required=False)
    subscription_sell_price = serializers.IntegerField(write_only=True, required=False)
    duration_days = serializers.IntegerField(write_only=True, required=False)
    period = serializers.CharField(write_only=True, required=False)

    core_features = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    subscription_features = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    subscription_feature = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "description",
            "is_active",
            "subscription_price",
            "subscription_sell_price",
            "duration_days",
            "period",
            "core_features",
            "subscription_features",
            "subscription_feature",
            "features",
            "prices",
        ]
        read_only_fields = ["features", "prices"]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # Extract lists (support both names for compatibility)
        core_features = validated_data.pop("core_features", []) or []
        subs_features = validated_data.pop("subscription_features", None)
        if subs_features is None:
            subs_features = validated_data.pop("subscription_feature", []) or []

        # Determine price and duration
        price = validated_data.pop("subscription_price", None)
        if price is None:
            price = validated_data.pop("subscription_sell_price", None)

        duration = validated_data.pop("duration_days", None) or 30
        period = validated_data.pop("period", None)
        if not period:
            # infer period from duration
            period = "yearly" if int(duration) >= 350 else "monthly"

        # create the subscription (plan)
        subscription = Subscription.objects.create(
            package_name=validated_data.get("package_name"),
            description=validated_data.get("description", None),
            is_active=validated_data.get("is_active", True),
            created_by=(
                user if user and getattr(user, "is_authenticated", False) else None
            ),
        )

        # create PlanPrice if price provided
        if price is not None:
            PlanPrice.objects.create(
                plan=subscription,
                period=period,
                price=price,
                duration_days=duration,
                created_by=(
                    user if user and getattr(user, "is_authenticated", False) else None
                ),
            )

        # Helper to normalize feature dict keys
        def _norm_feature(d):
            name = (
                d.get("feature")
                or d.get("feature_name")
                or d.get("featureCode")
                or d.get("feature_code")
            )
            enabled = (
                d.get("feature_status")
                if "feature_status" in d
                else d.get("is_enabled", True)
            )
            value = d.get("value") or d.get("count") or None
            is_unlimited = d.get("is_unlimited", False)
            code = d.get("feature_code") or d.get("featureCode") or None
            return {
                "feature_name": name,
                "is_enabled": bool(enabled),
                "value": value,
                "is_unlimited": bool(is_unlimited),
                "feature_code": code,
            }

        # create core features
        for f in core_features:
            nf = _norm_feature(f)
            SubscriptionFeature.objects.create(
                subscription=subscription,
                feature_name=nf["feature_name"],
                feature_code=nf.get("feature_code"),
                is_core=True,
                is_enabled=nf["is_enabled"],
                value=nf.get("value"),
                is_unlimited=nf.get("is_unlimited", False),
                created_by=(
                    user if user and getattr(user, "is_authenticated", False) else None
                ),
            )

        # create subscription-specific features
        for f in subs_features:
            nf = _norm_feature(f)
            SubscriptionFeature.objects.create(
                subscription=subscription,
                feature_name=nf["feature_name"],
                feature_code=nf.get("feature_code"),
                is_core=False,
                is_enabled=nf["is_enabled"],
                value=nf.get("value"),
                is_unlimited=nf.get("is_unlimited", False),
                created_by=(
                    user if user and getattr(user, "is_authenticated", False) else None
                ),
            )

        return subscription


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = "__all__"


class PlanPriceSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.package_name", read_only=True)

    class Meta:
        model = PlanPrice
        fields = ["id", "plan_name", "period", "price", "duration_days", "is_active"]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionInvoice
        fields = "__all__"
        read_only_fields = ["invoice_number"]


class PaymentSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSubscription
        fields = "__all__"
        read_only_fields = ["status", "razorpay_payment_id", "payment_date"]


from rest_framework import serializers

from subscription.models import Subscription
from subscription.services.pricing import calculate_price


class SubscriptionAPISerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    period = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    country_name = serializers.SerializerMethodField()
    state_name = serializers.SerializerMethodField()
    subscription_price = serializers.SerializerMethodField()
    subscription_discount = serializers.SerializerMethodField()
    subscription_sell_price = serializers.SerializerMethodField()
    plan_price = serializers.SerializerMethodField()
    core_features = serializers.SerializerMethodField()
    subscription_feature = serializers.SerializerMethodField()
    subscription_features = serializers.SerializerMethodField()
    no_of_profile_assessment = serializers.SerializerMethodField()
    no_of_tokens = serializers.SerializerMethodField()
    internship_access_type = serializers.SerializerMethodField()
    no_of_internship_access = serializers.SerializerMethodField()
    job_portal_access_type = serializers.SerializerMethodField()
    no_of_job_portal_access = serializers.SerializerMethodField()
    course_portal_access_type = serializers.SerializerMethodField()
    no_of_course_portal_access = serializers.SerializerMethodField()
    project_topic_access_type = serializers.SerializerMethodField()
    no_of_project_topic_access = serializers.SerializerMethodField()
    portal_access = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "description",
            "is_active",
            "subscription_price",
            "subscription_discount",
            "subscription_sell_price",
            "plan_price",
            "duration_days",
            "country",
            "state",
            "country_name",
            "state_name",
            "no_of_profile_assessment",
            "no_of_tokens",
            "core_features",
            "subscription_feature",
            "internship_access_type",
            "no_of_internship_access",
            "job_portal_access_type",
            "no_of_job_portal_access",
            "course_portal_access_type",
            "no_of_course_portal_access",
            "project_topic_access_type",
            "no_of_project_topic_access",
            "price",
            "period",
            "discounted_price",
            "discount_amount",
            "portal_access",
            "prices",
            "subscription_features",
        ]

    def _get_pricing(self, obj):
        if not hasattr(obj, "_pricing_cache"):
            plan_price = (
                obj.prices.filter(is_active=True, deleted=False)
                .order_by("-price")
                .first()
            )
            if not plan_price:
                obj._pricing_cache = {
                    "price": None,
                    "discount": 0,
                    "final_price": None,
                    "promo_code_applied": False,
                    "period": None,
                    "duration_days": None,
                }
            else:
                pricing = calculate_price(plan_price)
                pricing["period"] = plan_price.period
                pricing["duration_days"] = plan_price.duration_days
                obj._pricing_cache = pricing
        return obj._pricing_cache

    def get_price(self, obj):
        return self._get_pricing(obj)["price"]

    def get_period(self, obj):
        return self._get_pricing(obj)["period"]

    def get_duration_days(self, obj):
        return self._get_pricing(obj)["duration_days"]

    def get_discounted_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_discount_amount(self, obj):
        return self._get_pricing(obj)["discount"]

    def get_subscription_price(self, obj):
        return self._get_pricing(obj)["price"]

    def get_subscription_discount(self, obj):
        pricing = self._get_pricing(obj)
        price = pricing.get("price")
        discount = pricing.get("discount") or 0
        if not price or price <= 0:
            return 0
        percentage = (discount / price) * 100
        return (
            int(percentage) if float(percentage).is_integer() else round(percentage, 2)
        )

    def get_subscription_sell_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_plan_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_country(self, obj):
        return None

    def get_state(self, obj):
        return None

    def get_country_name(self, obj):
        return None

    def get_state_name(self, obj):
        return None

    def _serialize_feature_list(self, obj, is_core):
        features = obj.features.filter(is_core=is_core, deleted=False).order_by("id")
        return [
            {
                "feature_name": f.feature_name,
                "feature_status": bool(f.is_enabled),
            }
            for f in features
        ]

    def get_core_features(self, obj):
        return self._serialize_feature_list(obj, True)

    def get_subscription_feature(self, obj):
        return self._serialize_feature_list(obj, False)

    def get_subscription_features(self, obj):
        return self.get_subscription_feature(obj)

    def _feature_value_for_keyword(self, obj, keywords):
        features = obj.features.filter(deleted=False, is_enabled=True)
        for feature in features:
            name = (feature.feature_name or "").lower()
            code = (feature.feature_code or "").lower()
            if any(keyword in name or keyword in code for keyword in keywords):
                if feature.is_unlimited:
                    return None
                if feature.value is None:
                    return None
                try:
                    return int(feature.value)
                except (TypeError, ValueError):
                    return None
        return None

    def get_no_of_profile_assessment(self, obj):
        return self._feature_value_for_keyword(obj, ["assessment"])

    def get_no_of_tokens(self, obj):
        return self._feature_value_for_keyword(obj, ["token", "tokens"])

    def _access_type_for_keyword(self, obj, keywords):
        features = obj.features.filter(deleted=False, is_enabled=True)
        for feature in features:
            name = (feature.feature_name or "").lower()
            code = (feature.feature_code or "").lower()
            if any(keyword in name or keyword in code for keyword in keywords):
                if feature.is_unlimited:
                    return "full"
                if feature.value is None:
                    return "full"
                return "limited"
        return "none"

    def _feature_value_for_access(self, obj, keywords):
        features = obj.features.filter(deleted=False, is_enabled=True)
        for feature in features:
            name = (feature.feature_name or "").lower()
            code = (feature.feature_code or "").lower()
            if any(keyword in name or keyword in code for keyword in keywords):
                if feature.is_unlimited:
                    return None
                if feature.value is None:
                    return None
                try:
                    return int(feature.value)
                except (TypeError, ValueError):
                    return None
        return None

    def get_internship_access_type(self, obj):
        return self._access_type_for_keyword(obj, ["internship"])

    def get_no_of_internship_access(self, obj):
        return self._feature_value_for_access(obj, ["internship"])

    def get_job_portal_access_type(self, obj):
        return self._access_type_for_keyword(obj, ["job", "job_portal"])

    def get_no_of_job_portal_access(self, obj):
        return self._feature_value_for_access(obj, ["job", "job_portal"])

    def get_course_portal_access_type(self, obj):
        return self._access_type_for_keyword(obj, ["course", "course_portal"])

    def get_no_of_course_portal_access(self, obj):
        return self._feature_value_for_access(obj, ["course", "course_portal"])

    def get_project_topic_access_type(self, obj):
        return self._access_type_for_keyword(obj, ["project_topic", "project topic"])

    def get_no_of_project_topic_access(self, obj):
        return self._feature_value_for_access(obj, ["project_topic", "project topic"])

    def get_portal_access(self, obj):
        access_fields = [
            "assessment",
            "career_assessment",
            "domain_exploration",
            "skill_gap_analysis",
            "career_roadmap",
            "counsellor_session",
            "resume_builder",
            "job_recommendations",
            "learning_resources",
            "mock_interview",
            "mentorship_access",
            "premium_counsellor",
        ]
        features = list(obj.features.filter(deleted=False))
        access = {}
        for key in access_fields:
            enabled = any(
                (feature.feature_code or "").lower() == key
                or (feature.feature_name or "").lower() == key
                or key in (feature.feature_name or "").lower()
                or key in (feature.feature_code or "").lower()
                for feature in features
                if feature.is_enabled
            )
            access[key] = enabled
        return access

    prices = serializers.SerializerMethodField()

    def get_prices(self, obj):
        prices = obj.prices.filter(is_active=True, deleted=False)
        return [
            {
                "id": p.id,
                "period": p.period,
                "price": p.price,
                "duration_days": p.duration_days,
            }
            for p in prices
        ]
