from django.conf import settings
from django.db import models
from django.utils.timezone import now

from company.models import Company
from user.models import User


class Subscription(models.Model):
    package_name = models.CharField(max_length=100)
    # price = models.FloatField()
    price = models.IntegerField(db_column="subscription_price")
    duration_days = models.IntegerField()
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcription_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.package_name


class SubscriptionFeature(models.Model):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="features"
    )
    feature_name = models.CharField(max_length=150)
    is_core = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscription_feature_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subscription_feature_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscription_feature_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.subscription.package_name} - {self.feature_name}"


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_subcription_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_subcription_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_subcription_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.subscription.package_name}"


# Getting active Subscription for a company:

# UserSubscription.objects.filter(
#     company=company,
#     is_active=True,
#     end_date__gte=today
# ).exists()


class PaymentSubscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)

    # pricing snapshot (IMPORTANT for history)
    amount = models.FloatField()  # original price
    discount_amount = models.FloatField(default=0)
    final_amount = models.FloatField()  # after discount

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # razorpay
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)

    # optional but acceptable
    check_out_url = models.URLField(null=True, blank=True)

    # analytics-supporting (VALID to keep)
    currency = models.CharField(max_length=10, default="INR")
    payment_method = models.CharField(max_length=30, null=True, blank=True)

    payment_date = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payment_subcription_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="payment_subcription_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_subcription_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} - {self.final_amount} - {self.status}"


class SubscriptionInvoice(models.Model):
    INVOICE_TYPE_CHOICES = [
        ("proforma", "Proforma"),
        ("final", "Final"),
    ]

    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    invoice_type = models.CharField(
        max_length=10, choices=INVOICE_TYPE_CHOICES, default="proforma"
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)

    amount = models.FloatField()
    gst_rate = models.FloatField(default=18)

    cgst = models.FloatField(default=0)
    sgst = models.FloatField(default=0)
    total = models.FloatField()

    invoice_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    payment = models.ForeignKey(
        PaymentSubscription, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_invoice_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_invoice_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcription_invoice_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.invoice_number or 'Proforma'}"


class Discount(models.Model):
    name = models.CharField(max_length=100)

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, null=True, blank=True
    )  # null = global discount

    discount_type = models.CharField(
        choices=[("percent", "Percent"), ("flat", "Flat")], max_length=10
    )
    value = models.FloatField()

    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="discount_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="discount_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="discount_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
