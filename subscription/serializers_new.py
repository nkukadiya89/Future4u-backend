from django.utils.timezone import now
from rest_framework import serializers

from .models import (Discount, PaymentSubscription, PlanPrice, Subscription,
                     SubscriptionFeature, SubscriptionInvoice,
                     UserSubscription)


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
            {"id": p.id, "period": p.period, "price": p.price, "duration_days": p.duration_days}
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

    core_features = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    subscription_features = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    subscription_feature = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)

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
        ]

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
            created_by=user if user and getattr(user, "is_authenticated", False) else None,
        )

        # create PlanPrice if price provided
        if price is not None:
            PlanPrice.objects.create(
                plan=subscription,
                period=period,
                price=price,
                duration_days=duration,
                created_by=user if user and getattr(user, "is_authenticated", False) else None,
            )

        # Helper to normalize feature dict keys
        def _norm_feature(d):
            name = d.get("feature") or d.get("feature_name") or d.get("featureCode") or d.get("feature_code")
            enabled = d.get("feature_status") if "feature_status" in d else d.get("is_enabled", True)
            value = d.get("value") or d.get("count") or None
            is_unlimited = d.get("is_unlimited", False)
            code = d.get("feature_code") or d.get("featureCode") or None
            return {"feature_name": name, "is_enabled": bool(enabled), "value": value, "is_unlimited": bool(is_unlimited), "feature_code": code}

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
                created_by=user if user and getattr(user, "is_authenticated", False) else None,
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
                created_by=user if user and getattr(user, "is_authenticated", False) else None,
            )

        return subscription

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "description",
            "is_active",
            "features",
            "prices",
        ]


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

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "description",
            "is_active",
            "discounted_price",
            "discount_amount",
            "prices",
        ]

    def _get_pricing(self, obj):
        # Determine a PlanPrice to calculate pricing for. Use first active price.
        if not hasattr(obj, "_pricing_cache"):
            plan_price = (
                obj.prices.filter(is_active=True, deleted=False).order_by("-price").first()
            )
            if not plan_price:
                raise Exception("No active price available for subscription")
            obj._pricing_cache = calculate_price(plan_price)
        return obj._pricing_cache

    def get_discounted_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_discount_amount(self, obj):
        return self._get_pricing(obj)["discount"]

    prices = serializers.SerializerMethodField()

    def get_prices(self, obj):
        prices = obj.prices.filter(is_active=True, deleted=False)
        return [
            {"id": p.id, "period": p.period, "price": p.price, "duration_days": p.duration_days}
            for p in prices
        ]
