from django.contrib import admin

from common.mixins.admin_mixins import RelatedDataAdminMixin
from subscription.models import (Discount, FeatureUsage, PaymentSubscription,
                                 PlanPrice, PromoCode, Subscription,
                                 SubscriptionFeature, SubscriptionInvoice,
                                 UserSubscription)


class PlanPriceInline(admin.TabularInline):
    model = PlanPrice
    fields = ("period", "price", "duration_days", "is_active")
    extra = 0


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "package_name",
        "description",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("package_name", "description")
    inlines = [PlanPriceInline]


admin.site.register(Subscription, SubscriptionAdmin)


class SubscriptionFeatureAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("subscription",)
    list_display = (
        "id",
        "subscription__package_name",
        "feature_name",
        "feature_code",
        "is_enabled",
    )
    list_filter = ("is_enabled",)
    search_fields = ("subscription__package_name", "feature_name")


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
    search_fields = ("user__username", "user__email")


admin.site.register(SubscriptionInvoice, SubscriptionInvoiceAdmin)


class PaymentSubscriptionAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("user", "plan_price__plan")
    list_display = (
        "id",
        "user__first_name",
        "get_plan",
        "payment_method",
        "payment_date",
        "amount",
        "discount_amount",
        "final_amount",
        "status",
    )
    list_filter = ("payment_method", "status")
    search_fields = (
        "user__username",
        "user__email",
        "plan_price__plan__package_name",
        "razorpay_order_id",
    )

    def get_plan(self, obj):
        return getattr(getattr(obj.plan_price, "plan", None), "package_name", None)

    get_plan.short_description = "Plan"


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


class PlanPriceAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("plan",)
    list_display = ("id", "plan", "period", "price", "duration_days", "is_active")
    list_filter = ("period", "is_active")
    search_fields = ("plan__package_name",)


admin.site.register(PlanPrice, PlanPriceAdmin)


class UserSubscriptionAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("user", "plan_price__plan")
    list_display = (
        "id",
        "user",
        "get_plan",
        "start_date",
        "end_date",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("user__email", "plan_price__plan__package_name")

    def get_plan(self, obj):
        return getattr(getattr(obj.plan_price, "plan", None), "package_name", None)

    get_plan.short_description = "Plan"


admin.site.register(UserSubscription, UserSubscriptionAdmin)


class FeatureUsageAdmin(RelatedDataAdminMixin, admin.ModelAdmin):
    select_related_fields = ("user", "plan_price__plan")
    list_display = ("id", "user", "feature_code", "used", "plan_price", "last_used_at")
    list_filter = ("feature_code",)
    search_fields = ("user__email", "feature_code")


admin.site.register(FeatureUsage, FeatureUsageAdmin)
