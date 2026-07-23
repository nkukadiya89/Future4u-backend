from rest_framework import serializers

from .models import (
    PaymentSubscription,
    PlanPrice,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
    UserSubscription,
)
from subscription.services.pricing import PricingService, calculate_price
from subscription.services.feature_service import FeatureService
from user.serializers import UserQuickSerializer
from utils.datetime_formatter import format_datetime


class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ["id", "feature_name", "feature_code", "is_enabled"]


class SubscriptionWriteSerializer(serializers.ModelSerializer):
    subscription_price = serializers.IntegerField(write_only=True, required=False)
    subscription_discount = serializers.IntegerField(write_only=True, required=False)
    subscription_sell_price = serializers.IntegerField(write_only=True, required=False)
    plan_price = serializers.IntegerField(write_only=True, required=False)
    duration_days = serializers.IntegerField(write_only=True, required=False)

    core_features = serializers.ListField(
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
            "subscription_discount",
            "subscription_sell_price",
            "duration_days",
            "plan_price",
            "no_of_profile_assessment",
            "no_of_tokens",
            "internship_access_type",
            "no_of_internship_access",
            "job_portal_access_type",
            "no_of_job_portal_access",
            "course_portal_access_type",
            "no_of_course_portal_access",
            "project_topic_access_type",
            "no_of_project_topic_access",
            "career_compare",
            "career_roadmap",
            "ai_chat_access",
            "core_features",
            "subscription_feature",
        ]
        extra_kwargs = {
            "no_of_profile_assessment": {"required": False},
            "no_of_tokens": {"required": False},
            "internship_access_type": {"required": False},
            "no_of_internship_access": {"required": False, "allow_null": True},
            "job_portal_access_type": {"required": False},
            "no_of_job_portal_access": {"required": False, "allow_null": True},
            "course_portal_access_type": {"required": False},
            "no_of_course_portal_access": {"required": False, "allow_null": True},
            "project_topic_access_type": {"required": False},
            "no_of_project_topic_access": {"required": False, "allow_null": True},
            "career_compare": {"required": False},
            "career_roadmap": {"required": False},
            "ai_chat_access": {"required": False},
        }

    @staticmethod
    def _get_user(context):
        request = context.get("request")
        user = getattr(request, "user", None)
        return user if user and getattr(user, "is_authenticated", False) else None

    def validate(self, data):
        pairs = [
            ("internship_access_type", "no_of_internship_access", "Internship"),
            ("job_portal_access_type", "no_of_job_portal_access", "Job Portal"),
            ("course_portal_access_type", "no_of_course_portal_access", "Course Portal"),
            ("project_topic_access_type", "no_of_project_topic_access", "Project Topic"),
        ]
        for type_field, count_field, label in pairs:
            if type_field in data and data[type_field] == "limited":
                count_val = data.get(count_field)
                if count_val is None or count_val <= 0:
                    raise serializers.ValidationError(
                        f"Count is required for {label} when access type is 'limited'."
                    )
        return data

    def _save(self, validated_data, instance=None):
        user = self._get_user(self.context)
        price_data = PricingService.extract(validated_data)
        core_features_data = validated_data.pop("core_features", None)
        subs_features = validated_data.pop("subscription_feature", None)
        is_update = instance is not None

        if instance is None:
            # Remove pricing-only fields before create
            for key in ("subscription_price", "subscription_discount",
                        "subscription_sell_price", "plan_price", "duration_days"):
                validated_data.pop(key, None)
            instance = Subscription.objects.create(**validated_data, created_by=user)
        else:
            for attr, value in validated_data.items():
                if attr not in ("subscription_price", "subscription_discount",
                                "subscription_sell_price", "plan_price", "duration_days"):
                    setattr(instance, attr, value)
            instance.updated_by = user
            instance.save()

        if core_features_data:
            for item in core_features_data:
                code = item.get("feature_code", "").strip()
                status = bool(item.get("feature_status", True))
                if code == "career_compare":
                    instance.career_compare = status
                elif code == "career_roadmap":
                    instance.career_roadmap = status
                elif code == "ai_chat":
                    instance.ai_chat_access = status
            instance.save()

        PricingService.save(instance, price_data, user, update=is_update)
        FeatureService.sync_custom_features(
            instance, subs_features, user
        )

        return instance

    def create(self, validated_data):
        return self._save(validated_data)

    def update(self, instance, validated_data):
        return self._save(validated_data, instance=instance)


SubscriptionCreateSerializer = SubscriptionWriteSerializer


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = "__all__"


class UserSubscriptionMeSerializer(serializers.Serializer):
    subscription = serializers.SerializerMethodField()
    period = serializers.CharField(source="plan_price.period", read_only=True)
    start_date = serializers.DateField(read_only=True)
    end_date = serializers.DateField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    core_features = serializers.SerializerMethodField()
    limits = serializers.SerializerMethodField()
    subscription_feature = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "subscription", "period", "start_date", "end_date",
            "is_active", "core_features", "limits", "subscription_feature",
        ]

    def get_subscription(self, obj):
        plan = getattr(obj.plan_price, "plan", None)
        if not plan:
            return None
        return {"id": plan.id, "package_name": plan.package_name}

    def get_core_features(self, obj):
        plan = getattr(obj.plan_price, "plan", None)
        if not plan:
            return []
        return [
            {"feature_code": "career_compare", "feature_status": plan.career_compare},
            {"feature_code": "career_roadmap", "feature_status": plan.career_roadmap},
            {"feature_code": "ai_chat", "feature_status": plan.ai_chat_access},
        ]

    def get_limits(self, obj):
        plan = getattr(obj.plan_price, "plan", None)
        if not plan:
            return {}

        from subscription.models import FeatureUsage
        usage_qs = FeatureUsage.objects.filter(
            user=getattr(obj, "user", None),
            plan_price=obj.plan_price,
        )
        usage = {u.feature_code: u.used for u in usage_qs}

        def _entry(code, allowed, unlimited=False):
            used = usage.get(code, 0)
            if unlimited:
                return {"allowed": "unlimited", "used": used, "remaining": None}
            return {
                "allowed": allowed,
                "used": used,
                "remaining": max(allowed - used, 0),
            }

        return {
            "profile_assessment": _entry("assessment", plan.no_of_profile_assessment),
            "monthly_tokens": _entry("monthly_tokens", plan.no_of_tokens),
            "internship": _entry(
                "internship",
                plan.no_of_internship_access or 0,
                plan.internship_access_type == "full",
            ),
            "job": _entry(
                "job",
                plan.no_of_job_portal_access or 0,
                plan.job_portal_access_type == "full",
            ),
            "course": _entry(
                "course",
                plan.no_of_course_portal_access or 0,
                plan.course_portal_access_type == "full",
            ),
            "project_topic": _entry(
                "project_topic",
                plan.no_of_project_topic_access or 0,
                plan.project_topic_access_type == "full",
            ),
        }

    def get_subscription_feature(self, obj):
        plan = getattr(obj.plan_price, "plan", None)
        if not plan:
            return []
        return [
            {"feature_name": f.feature_name, "feature_status": bool(f.is_enabled)}
            for f in SubscriptionFeature.objects.filter(
                subscription=plan, deleted=False
            ).order_by("id")
        ]


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


class SubscriptionSerializer(serializers.ModelSerializer):
    subscription_price = serializers.SerializerMethodField()
    subscription_discount = serializers.SerializerMethodField()
    subscription_sell_price = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()

    core_features = serializers.SerializerMethodField()

    subscription_feature = serializers.SerializerMethodField()

    created_by = UserQuickSerializer(read_only=True)
    updated_by = UserQuickSerializer(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

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
            "duration_days",
            "no_of_profile_assessment",
            "no_of_tokens",
            "internship_access_type",
            "no_of_internship_access",
            "job_portal_access_type",
            "no_of_job_portal_access",
            "course_portal_access_type",
            "no_of_course_portal_access",
            "project_topic_access_type",
            "no_of_project_topic_access",
            "career_compare",
            "career_roadmap",
            "ai_chat_access",
            "core_features",
            "subscription_feature",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "no_of_profile_assessment",
            "no_of_tokens",
            "internship_access_type",
            "no_of_internship_access",
            "job_portal_access_type",
            "no_of_job_portal_access",
            "course_portal_access_type",
            "no_of_course_portal_access",
            "project_topic_access_type",
            "no_of_project_topic_access",
            "career_compare",
            "career_roadmap",
            "ai_chat_access",
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

    def get_duration_days(self, obj):
        return self._get_pricing(obj)["duration_days"]

    def get_core_features(self, obj):
        return [
            {"feature_code": "career_compare", "feature_status": obj.career_compare},
            {"feature_code": "career_roadmap", "feature_status": obj.career_roadmap},
            {"feature_code": "ai_chat", "feature_status": obj.ai_chat_access},
        ]

    def get_created_at(self, obj):
        return format_datetime(obj.created_at)

    def get_updated_at(self, obj):
        return format_datetime(obj.updated_at)

    def get_subscription_feature(self, obj):
        features = obj.features.filter(
            deleted=False
        ).order_by("id")
        return [
            {
                "feature_name": f.feature_name,
                "feature_status": bool(f.is_enabled),
            }
            for f in features
        ]


SubscriptionAPISerializer = SubscriptionSerializer
