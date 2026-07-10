from django.utils.timezone import now
from rest_framework import serializers

from .models import (
    Discount,
    PaymentSubscription,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
    UserSubscription,
)


class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ["id", "feature_name", "is_core", "is_enabled"]


class SubscriptionSerializer(serializers.ModelSerializer):
    features = SubscriptionFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "price",
            "duration_days",
            "description",
            "is_active",
            "features",
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = "__all__"


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
            "price",
            "duration_days",
            "description",
            "is_active",
            "discounted_price",
            "discount_amount",
        ]

    def _get_pricing(self, obj):
        if not hasattr(obj, "_pricing_cache"):
            obj._pricing_cache = calculate_price(obj)
        return obj._pricing_cache

    def get_discounted_price(self, obj):
        return self._get_pricing(obj)["final_price"]

    def get_discount_amount(self, obj):
        return self._get_pricing(obj)["discount"]
