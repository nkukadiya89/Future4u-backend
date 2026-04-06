from django.utils.timezone import now
from rest_framework import serializers

from company.models import Company

# from site_location.models import SiteLocation
from subscription.models import (
    PaymentSubscription,
    Subscription,
    SubscriptionCart,
    SubscriptionCartWithSite,
    SubscriptionFeature,
    SubscriptionInvoice,
)
from utils.datetime_formatter import format_datetime
from utils.invoice_number import generate_invoice, generate_invoice_number


# Subscription
class SubscriptionSerializer(serializers.ModelSerializer):
    subscription_feature = serializers.ListField(required=False)
    core_features = serializers.ListField(required=False)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "subscription_price",
            "subscription_discount",
            "subscription_sell_price",
            "plan_price",
            "duration_days",
            "description",
            "core_features",
            "subscription_feature",
            "created_by",
            "updated_by",
            "deleted_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
            "deleted_by": {"write_only": True},
        }

    def create(self, validated_data):
        subscription_features_data = validated_data.pop("subscription_feature", [])
        core_features_data = validated_data.pop("core_features", [])

        if "created_at" not in validated_data:
            validated_data["created_at"] = now()

        subscription_instance = Subscription.objects.create(**validated_data)

        feature_instances = []

        # Save core features (is_core=True)
        for data in core_features_data:
            payload = {
                "subscription_id": subscription_instance.id,
                "feature_name": data.get("feature_name"),
                "feature_status": data.get("feature_status", False),
                "is_core": True,
            }
            if (
                payload["feature_name"] is not None
                and payload["feature_status"] is not None
            ):
                feature_instances.append(SubscriptionFeature.objects.create(**payload))

        # Save custom features (is_core=False)
        for data in subscription_features_data:
            payload = {
                "subscription_id": subscription_instance.id,
                "feature_name": data.get("feature_name"),
                "feature_status": data.get("feature_status", False),
                "is_core": False,
            }
            if (
                payload["feature_name"] is not None
                and payload["feature_status"] is not None
            ):
                feature_instances.append(SubscriptionFeature.objects.create(**payload))

        return subscription_instance

    def update(self, instance, validated_data):
        subscription_features_data = validated_data.pop("subscription_feature", [])
        core_features_data = validated_data.pop("core_features", [])

        # audit: updated_at timestamp
        # instance.updated_at = now()
        validated_data["updated_at"] = now()
        instance = super(SubscriptionSerializer, self).update(instance, validated_data)

        # Replace all features when provided
        SubscriptionFeature.objects.filter(subscription_id=instance.id).delete()

        # Core features
        for data in core_features_data:
            if data.get("feature_name") is None:
                continue
            SubscriptionFeature.objects.create(
                subscription_id=instance.id,
                feature_name=data.get("feature_name"),
                feature_status=data.get("feature_status", False),
                is_core=True,
            )

        # Custom features
        for data in subscription_features_data:
            if data.get("feature_name") is None:
                continue
            SubscriptionFeature.objects.create(
                subscription_id=instance.id,
                feature_name=data.get("feature_name"),
                feature_status=data.get("feature_status", False),
                is_core=False,
            )

        return instance

    def validate(self, attrs):
        sub_type = attrs.get("subscription_type") or getattr(
            self.instance, "subscription_type", None
        )
        errors = {}

        if sub_type == "subscription":
            # Require both device and subscription pricing fields
            for f in [
                "subscription_price",
                "subscription_discount",
                "subscription_sell_price",
            ]:
                if self.instance is None and attrs.get(f) in [None, ""]:
                    errors[f] = "This field is required for subscription type"

        if errors:
            raise serializers.ValidationError(errors)
        return attrs


# subscription Delete
class SubscriptionArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Subscription
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                subscription = Subscription.objects.get(id=deleted_id)
                subscription.deleted = True
                subscription.deleted_at = now()
                request = (
                    self.context.get("request") if hasattr(self, "context") else None
                )
                if request and hasattr(request, "user"):
                    subscription.deleted_by = request.user
                subscription.save()
            except Subscription.DoesNotExist:
                raise serializers.ValidationError("Subscription does not exist")
        return subscription


# subscription Restore
class SubscriptionRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Subscription
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                subscription = Subscription.objects.get(id=deleted_id)
                subscription.deleted = False
                subscription.deleted_at = None
                subscription.deleted_by = None
                subscription.updated_at = now()
                subscription.save()
            except Subscription.DoesNotExist:
                raise serializers.ValidationError("Subscription does not exist")
        return subscription


class SubscriptionArchiveListSerializer(serializers.ModelSerializer):
    core_features = serializers.SerializerMethodField()
    subscription_feature = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    deleted_by_name = serializers.SerializerMethodField()

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return (
            f"{obj.created_by.first_name} {obj.created_by.last_name}"
            if obj.created_by
            else None
        )

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return (
            f"{obj.updated_by.first_name} {obj.updated_by.last_name}"
            if obj.updated_by
            else None
        )

    def get_deleted_at(self, obj):
        return format_datetime(getattr(obj, "deleted_at", None))

    def get_deleted_by_name(self, obj):
        return (
            f"{obj.deleted_by.first_name} {obj.deleted_by.last_name}"
            if obj.deleted_by
            else None
        )

    def get_core_features(self, instance):
        features = SubscriptionFeature.objects.filter(
            subscription_id=instance.id, is_core=True
        )
        return [
            {
                "id": f.id,
                "feature_name": f.feature_name,
                "feature_status": f.feature_status,
            }
            for f in features
        ]

    def get_subscription_feature(self, instance):
        features = SubscriptionFeature.objects.filter(
            subscription_id=instance.id, is_core=False
        )
        return [
            {
                "id": f.id,
                "feature_name": f.feature_name,
                "feature_status": f.feature_status,
            }
            for f in features
        ]

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "subscription_price",
            "subscription_discount",
            "subscription_sell_price",
            "plan_price",
            "duration_days",
            "description",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
            "core_features",
            "subscription_feature",
        ]


# Subscription Feature
class SubscriptionFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionFeature
        fields = ["id", "subscription", "feature_name", "feature_status"]


class SubscriptionGetSerializer(serializers.ModelSerializer):
    core_features = serializers.SerializerMethodField()
    subscription_feature = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return (
            f"{obj.created_by.first_name} {obj.created_by.last_name}"
            if obj.created_by
            else None
        )

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return (
            f"{obj.updated_by.first_name} {obj.updated_by.last_name}"
            if obj.updated_by
            else None
        )

    def get_core_features(self, instance):
        features = SubscriptionFeature.objects.filter(
            subscription_id=instance.id, is_core=True
        )
        return [
            {
                "id": f.id,
                "feature_name": f.feature_name,
                "feature_status": f.feature_status,
            }
            for f in features
        ]

    def get_subscription_feature(self, instance):
        features = SubscriptionFeature.objects.filter(
            subscription_id=instance.id, is_core=False
        )
        return [
            {
                "id": f.id,
                "feature_name": f.feature_name,
                "feature_status": f.feature_status,
            }
            for f in features
        ]

    class Meta:
        model = Subscription
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "subscription_price",
            "subscription_discount",
            "subscription_sell_price",
            "plan_price",
            "duration_days",
            "description",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "core_features",
            "subscription_feature",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


class TransferSubscriptionSerializer(SubscriptionGetSerializer):
    class Meta(SubscriptionGetSerializer.Meta):
        fields = [
            "id",
            "package_name",
            "subscription_type",
            "plan_price",
            "description",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
        ]


# subscription Status
class SubscriptionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ["status"]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    invoice_date = serializers.DateField(
        input_formats=["%d-%m-%y"],
        format="%d-%m-%y",
    )
    due_date = serializers.DateField(
        input_formats=["%d-%m-%y"],
        format="%d-%m-%y",
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
        )
        instance.save()

        return instance


# Subscription Invoice Delete
class SubscriptionInvoiceArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                purchasedsubscription = SubscriptionInvoice.objects.get(id=deleted_id)
                purchasedsubscription.deleted = True
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
                purchasedsubscription.deleted = False
                purchasedsubscription.updated_at = now()
                purchasedsubscription.save()
            except SubscriptionInvoice.DoesNotExist:
                raise serializers.ValidationError(
                    "Purchased Subscription does not exist"
                )

        return purchasedsubscription


class PaymentSubscriptionSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    subscription_name = serializers.CharField(
        source="subscription.package_name", read_only=True
    )

    class Meta:
        model = PaymentSubscription
        fields = "__all__"


class CartAddSerializer(serializers.Serializer):
    company = serializers.IntegerField()
    subscription = serializers.IntegerField()
    quantity = serializers.IntegerField()


class CartModifySerializer(serializers.Serializer):
    company = serializers.IntegerField()
    subscription = serializers.IntegerField()


class CartSetQuantitySerializer(serializers.Serializer):
    company = serializers.IntegerField()
    subscription = serializers.IntegerField()


class SubscriptionCartSerializer(serializers.ModelSerializer):
    subscription_name = serializers.CharField(
        source="subscription.package_name", read_only=True
    )

    class Meta:
        model = SubscriptionCart
        fields = ["id", "company", "subscription", "subscription_name", "quantity"]


class CartSummarySerializer(serializers.Serializer):

    def to_representation(self, cart_rows):
        plans = []
        sub_total = 0.0
        for row in cart_rows:
            price = float(row.subscription.subscription_sell_price)
            plans.append(
                {
                    "subscription_id": row.subscription_id,
                    "subscription_name": row.subscription.package_name,
                    "price_per_device": price,
                    "line_total": round(price, 2),
                }
            )
            sub_total += price

        gst_rate = 18
        gst_amount = round(sub_total * (gst_rate / 100.0), 2)
        grand_total = round(sub_total + gst_amount, 2)

        return {
            "plans": plans,
            "order_summary": {
                "sub_total": round(sub_total, 2),
                "gst_rate": gst_rate,
                "gst_amount": gst_amount,
                "grand_total": grand_total,
            },
        }


class AddToCartWithSiteSerializer(serializers.Serializer):
    company = serializers.IntegerField()
    subscription = serializers.IntegerField()
    quantity = serializers.IntegerField()
    site = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = SubscriptionCartWithSite
        fields = ["id", "company", "subscription", "site", "quantity", "created_at"]

        extra_kwargs = {
            "company": {"required": True},
            "subscription": {"required": True},
            "quantity": {"required": True, "min_value": 1},
        }

    def validate(self, data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        user_company = request.user.company

        if data["company"] != user_company.id:
            raise serializers.ValidationError("You can only use your own company.")

        try:
            data["company_instance"] = Company.objects.get(id=data["company"])
        except Company.DoesNotExist:
            raise serializers.ValidationError("Company not found.")

        try:
            data["subscription_instance"] = Subscription.objects.get(
                id=data["subscription"]
            )
        except Subscription.DoesNotExist:
            raise serializers.ValidationError("Subscription not found.")

        return data

    def to_representation(self, instance):
        representation = {
            "id": instance.id,
            "company": instance.company.id,
            "subscription": instance.subscription.id,
            "quantity": instance.quantity,
            "site": list(instance.sites.values_list("id", flat=True)),
            "created_at": instance.created_at.isoformat(),
        }
        return representation


class SalesRevenueReportSerializer(serializers.Serializer):
    month = serializers.CharField(max_length=20)
    sales = serializers.FloatField()
    subscription_count = serializers.IntegerField()

    class Meta:
        fields = ["month", "sales", "subscription_count"]


class DeviceStatusReportSerializer(serializers.Serializer):
    month = serializers.CharField(max_length=20)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically add fields for each subscription package
        if args and isinstance(args[0], list) and args[0]:
            # Get all unique field names from the data
            field_names = set()
            for item in args[0]:
                field_names.update(item.keys())

            # Add dynamic integer fields for each package
            for field_name in field_names:
                if field_name != "month":
                    self.fields[field_name] = serializers.IntegerField()
