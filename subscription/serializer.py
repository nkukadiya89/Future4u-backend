from rest_framework import serializers

from subscription.models import (
    PaymentSubscription,
    PurchasedSubscription,
    StripeCharge,
    Subcription,
    SubscriptionFeature,
    SubscriptionInvoice,
)
from utils.invoice_number import generate_invoice, generate_invoice_number


class StripeChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StripeCharge
        fields = [
            "id",
            "stripe_id",
            "amount",
            "currency",
            "description",
            "status",
            "paid",
            "captured",
            "payment_method",
            "company",
            "invoice_no",
            "fiscal_year",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


# Subscription
class SubcriptionSerializer(serializers.ModelSerializer):
    subscription_feature = serializers.ListField(required=False)

    class Meta:
        model = Subcription
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "per_user_price",
            "discount",
            "sell_price",
            "duration",
            "description",
            "status",
            "subscription_feature",
        ]

    def create(self, validated_data):
        subscription_features_data = validated_data.pop("subscription_feature", None)

        subscription_instance = Subcription.objects.create(**validated_data)

        feature_instances = []

        for data in subscription_features_data:
            data["subcription_id"] = subscription_instance.id  # type: ignore
            if data.get("feature_name") and data.get("feature_status") is not None:
                feature = SubscriptionFeature.objects.create(**data)
                feature_instances.append(feature)

        return subscription_instance

    def update(self, instance, validated_data):
        subscription_features_data = validated_data.pop("subscription_feature", [])

        instance = super(SubcriptionSerializer, self).update(instance, validated_data)

        SubscriptionFeature.objects.filter(subcription_id=instance).delete()

        for subscription_feature in subscription_features_data:
            feature_name = subscription_feature["feature_name"]
            SubscriptionFeature.objects.get_or_create(
                subcription_id=instance.id,
                feature_name=feature_name,
                defaults={
                    "feature_name": subscription_feature["feature_name"],
                    "feature_status": subscription_feature["feature_status"],
                },
            )

        return instance


# subcription Delete
class SubcriptionDeleteSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Subcription
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                subcription = Subcription.objects.get(id=deleted_id)
                subcription.deleted = 1
                subcription.save()
            except Subcription.DoesNotExist:
                raise serializers.ValidationError("Subcription does not exist")
        return subcription


# subcription Restore
class SubcriptionRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Subcription
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                subcription = Subcription.objects.get(id=deleted_id)
                subcription.deleted = 0
                subcription.save()
            except Subcription.DoesNotExist:
                raise serializers.ValidationError("Subscription does not exist")
        return subcription


# Subscription Feature
class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ["id", "subcription", "feature_name", "feature_status"]


class SubcriptionGetSerializer(serializers.ModelSerializer):
    subscription_feature = serializers.SerializerMethodField()

    def get_subscription_feature(self, instance):
        subscription_features = SubscriptionFeature.objects.filter(
            subcription_id=instance.id
        )
        if subscription_features:
            return [
                {
                    "id": subscription_feature.id,  # type: ignore
                    "feature_name": subscription_feature.feature_name,
                    "feature_status": subscription_feature.feature_status,
                }
                for subscription_feature in subscription_features
            ]
        else:
            return [
                {
                    "feature_name": None,
                    "feature_status": None,
                }
            ]

    class Meta:
        model = Subcription
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "per_user_price",
            "discount",
            "sell_price",
            "duration",
            "description",
            "status",
            "created_by",
            "updated_by",
            "subscription_feature",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


# subcription Status
class SubcriptionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subcription
        fields = ["status"]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    invoice_date = serializers.DateField(
        input_formats=["%d-%m-%y"],
        format="%d-%m-%y",  # type: ignore
    )
    due_date = serializers.DateField(
        input_formats=["%d-%m-%y"],
        format="%d-%m-%y",  # type: ignore
    )
    invoice_number = serializers.CharField(read_only=True)
    currency_name = serializers.CharField(
        source="currency.currency_name", required=False
    )
    subscription_name = serializers.CharField(
        source="subscription.package_name", required=False
    )

    business_name = serializers.CharField(source="company.name", required=False)
    address = serializers.CharField(source="company.address_line_1", required=False)
    city = serializers.CharField(source="company.city", required=False)
    state = serializers.CharField(source="company.state", required=False)
    email = serializers.CharField(source="company.email", required=False)
    pincode_number = serializers.CharField(source="company.pincode", required=False)

    class Meta:
        model = SubscriptionInvoice
        fields = [
            "id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "company",
            "business_name",
            "address",
            "city",
            "state",
            "email",
            "pincode_number",
            "currency",
            "currency_name",
            "subscription",
            "subscription_name",
            "invoice_type",
            "quantity",
            "sell_price",
            "gst_rate",
            "amount",
            "note",
            "cgst",
            "sgst",
            "total",
            "payment_reference_id",
            "check_out_url",
            "active",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def create(self, validated_data):
        invoice_type = validated_data.get("invoice_type")

        if invoice_type == "Performa Invoice":
            invoice_number = generate_invoice_number(self)

        else:
            invoice_type == "Commercial Invoice"

            invoice_number = generate_invoice(self)

        instance = SubscriptionInvoice(
            invoice_number=invoice_number,
            invoice_date=validated_data.get("invoice_date"),
            due_date=validated_data.get("due_date"),
            # Add other fields from validated_data
        )
        instance.save()

        return instance


# Subscription Invoice Delete
class SubscriptionInvoiceDeleteSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                purchasedsubscription = SubscriptionInvoice.objects.get(id=deleted_id)
                purchasedsubscription.deleted = 1
                purchasedsubscription.save()
            except SubscriptionInvoice.DoesNotExist:
                raise serializers.ValidationError(
                    "Purchased Subscription does not exist"
                )

        return purchasedsubscription


# Purchased Subscription Restore
class SubscriptionInvoiceRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                purchasedsubscription = SubscriptionInvoice.objects.get(id=deleted_id)
                purchasedsubscription.deleted = 0
                purchasedsubscription.save()
            except SubscriptionInvoice.DoesNotExist:
                raise serializers.ValidationError(
                    "Purchased Subscription does not exist"
                )

        return purchasedsubscription


class PurchasedSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasedSubscription
        fields = [
            "company",
            "subscription",
            "duration",
            "per_user_price",
            "discount",
            "sell_price",
            "payment_mode",
            "payment_reference_id",
            "start_date",
            "end_date",
        ]


class PaymentSubscriptionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    subscription_name = serializers.CharField(
        source="subscription.package_name", read_only=True
    )

    class Meta:
        model = PaymentSubscription
        fields = "__all__"
