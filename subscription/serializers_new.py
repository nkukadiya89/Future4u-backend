from rest_framework import serializers

from subscription.services.pricing import calculate_price

from .models import (PaymentSubscription, PlanPrice, Subscription,
                     SubscriptionFeature, SubscriptionInvoice,
                     UserSubscription)


class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    feature_status = serializers.BooleanField(source="is_enabled")

    class Meta:
        model = SubscriptionFeature
        fields = ["id", "feature_name", "feature_status", "is_core"]


class SubscriptionSerializer(serializers.ModelSerializer):
    features = SubscriptionFeatureSerializer(many=True, read_only=True)
    prices = serializers.SerializerMethodField()

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


class SubscriptionAPISerializer(serializers.ModelSerializer):
    discounted_price = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    prices = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

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
            "features",
        ]

    def _get_pricing(self, obj):
        if not hasattr(obj, "_pricing_cache"):
            plan_price = (
                obj.prices.filter(is_active=True, deleted=False).order_by("-price").first()
            )
            if not plan_price:
                return {"final_price": 0, "discount": 0}
            obj._pricing_cache = calculate_price(plan_price)
        return obj._pricing_cache

    def get_discounted_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_discount_amount(self, obj):
        return self._get_pricing(obj)["discount"]

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

    def get_features(self, obj):
        features = obj.features.filter(is_enabled=True, deleted=False)
        return [
            {
                "feature_name": feature.feature_name,
                "value": feature.value,
                "is_unlimited": feature.is_unlimited,
                "is_core": feature.is_core,
            }
            for feature in features
        ]


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """Writable serializer to accept admin/frontend subscription payload.

    Accepts nested fields for pricing and features and creates a `PlanPrice`
    and `SubscriptionFeature` rows when a new `Subscription` is created.
    """

    # legacy/frontend fields
    subscription_price = serializers.IntegerField(write_only=True, required=False)
    subscription_discount = serializers.FloatField(write_only=True, required=False)
    subscription_sell_price = serializers.FloatField(write_only=True, required=False)
    duration_days = serializers.IntegerField(write_only=True, required=False)

    # nested feature lists
    core_features = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )
    subscription_features = serializers.ListField(
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
            "core_features",
            "subscription_features",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        core_features = validated_data.pop("core_features", [])
        subscription_features = validated_data.pop("subscription_features", [])

        # pricing fields
        price = None
        if "subscription_price" in validated_data:
            price = validated_data.pop("subscription_price")
        elif "subscription_sell_price" in validated_data:
            price = validated_data.pop("subscription_sell_price")

        duration = validated_data.pop("duration_days", None) or 30

        # create subscription (plan)
        subscription = Subscription.objects.create(
            package_name=validated_data.get("package_name"),
            description=validated_data.get("description", None),
            is_active=validated_data.get("is_active", True),
            created_by=user if user and user.is_authenticated else None,
        )

        # create PlanPrice snapshot if price provided
        if price is not None:
            PlanPrice.objects.create(
                plan=subscription,
                period="monthly",
                price=price,
                duration_days=duration,
                created_by=user if user and user.is_authenticated else None,
            )

        # create core features
        for f in core_features:
            SubscriptionFeature.objects.create(
                subscription=subscription,
                feature_name=f.get("feature_name") or f.get("feature_code"),
                feature_code=f.get("feature_code") or None,
                is_core=True,
                is_enabled=bool(f.get("is_enabled", True)),
                value=f.get("value") or None,
                is_unlimited=bool(f.get("is_unlimited", False)),
                created_by=user if user and user.is_authenticated else None,
            )

        # create subscription-specific features
        for f in subscription_features:
            SubscriptionFeature.objects.create(
                subscription=subscription,
                feature_name=f.get("feature_name"),
                feature_code=f.get("feature_code") or None,
                is_core=False,
                is_enabled=bool(f.get("feature_status", f.get("is_enabled", True))),
                value=f.get("value") or None,
                is_unlimited=bool(f.get("is_unlimited", False)),
                created_by=user if user and user.is_authenticated else None,
            )

        return subscription
