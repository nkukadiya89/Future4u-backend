from django.contrib import admin

from common.mixins.admin_mixins import RelatedDataAdminMixin
from subscription.models import (
    Discount,
    PaymentSubscription,
    PromoCode,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
)


# Register your models here.
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "package_name",
        "price",
        "duration_days",
        "description",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("package_name", "description")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


admin.site.register(Subscription, SubscriptionAdmin)


class SubscriptionFeatureAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("subscription",)
    list_display = (
        "id",
        "subscription__package_name",
        "feature_name",
        "feature_code",
        "value",
        "is_unlimited",
        "is_core",
        "is_enabled",
    )
    list_filter = ("is_enabled", "is_core", "is_unlimited")
    search_fields = (
        "subscription__user__username",
        "subscription__user__email",
        "feature_name",
    )


admin.site.register(SubscriptionFeature, SubscriptionFeatureAdmin)


class SubscriptionInvoiceAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("user",)
    list_display = (
        "id",
        "invoice_number",
        "invoice_type",
        "user__first_name",
        "subscription",
        "amount",
        "gst_rate",
        "cgst",
        "sgst",
        "total",
        "invoice_date",
        "due_date",
    )
    list_filter = ("invoice_type", "invoice_number")
    search_fields = ("subscription__user__username", "subscription__user__email")


admin.site.register(SubscriptionInvoice, SubscriptionInvoiceAdmin)


class PaymentSubscriptionAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("user",)
    list_display = (
        "id",
        "user__first_name",
        "payment_method",
        "payment_date",
        "amount",
    )
    list_filter = ("payment_method", "status")
    search_fields = (
        "subscription__user__username",
        "subscription__user__email",
        "payment_method",
    )


admin.site.register(PaymentSubscription, PaymentSubscriptionAdmin)


class DiscountAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("subscription",)
    list_display = (
        "id",
        "name",
        "discount_type",
        "value",
        "is_active",
        "valid_from",
        "valid_to",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("subscription__package_name",)


admin.site.register(Discount, DiscountAdmin)


class PromoCodeAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("subscription",)
    list_display = (
        "id",
        "code",
        "discount_type",
        "value",
        "is_active",
        "valid_from",
        "valid_to",
        "usage_limit",
        "used_count",
    )
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)


admin.site.register(PromoCode, PromoCodeAdmin)
