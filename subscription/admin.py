from django.contrib import admin

from subscription.models import (
    Discount,
    PaymentSubscription,
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


class SubscriptionFeatureAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subscription__package_name",
        "feature_name",
        "is_core",
        "is_enabled",
    )
    list_filter = ("is_enabled", "is_core")
    search_fields = (
        "subscription__user__username",
        "subscription__user__email",
        "feature_name",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subscription")


admin.site.register(SubscriptionFeature, SubscriptionFeatureAdmin)


class SubscriptionInvoiceAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")


admin.site.register(SubscriptionInvoice, SubscriptionInvoiceAdmin)


class PaymentSubscriptionAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")


admin.site.register(PaymentSubscription, PaymentSubscriptionAdmin)


class DiscountAdmin(admin.ModelAdmin):
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("subscription")


admin.site.register(Discount, DiscountAdmin)
