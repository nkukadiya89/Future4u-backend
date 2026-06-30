from django.utils.timezone import now
from rest_framework import serializers

from .models import (
    Discount,
    PaymentSubscription,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
    UserSubscription,
    PlanPrice,
)


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
