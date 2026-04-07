from rest_framework import serializers

from .models import (
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
