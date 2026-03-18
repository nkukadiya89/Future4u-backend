from django.conf import settings
from django.db import models
from django.utils.timezone import now

from company.models import Company
from currency.models import Currency

# Enterpirse / peruser / on premise


class StripeCharge(models.Model):
    stripe_id = models.CharField(max_length=100)
    amount = models.FloatField(default=0)
    currency = models.CharField(max_length=5)
    description = models.TextField(null=True)
    status = models.CharField(max_length=10, verbose_name="status of payment")
    paid = models.BooleanField(
        default=False,
        verbose_name="if charge succeeded or authorized for later capture",
    )
    captured = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20)

    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING)
    invoice_no = models.IntegerField(default=0)
    fiscal_year = models.CharField(max_length=10, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stripe_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="stripe_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.amount}-{self.status}"

    class Meta:
        db_table = "stripe_charge"
        ordering = ["id"]


class Subcription(models.Model):
    SUBCRIPTION_CHOICES = (
        ("enterpirse", "Enterpirse"),
        ("peruser", "Peruser"),
        ("on_premise", "On-Premise"),
    )
    STATUS_CHOICES = (
        ("active", "active"),
        ("in_active", "in_active"),
    )
    package_name = models.CharField(max_length=100)
    subscription_type = models.CharField(
        max_length=50, choices=SUBCRIPTION_CHOICES, default="enterpirse"
    )
    per_user_price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    duration = models.CharField(max_length=150, null=True)
    description = models.TextField(null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="active")

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
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.package_name}"

    class Meta:
        db_table = "subcription"


class SubscriptionFeature(models.Model):
    subcription = models.ForeignKey(Subcription, on_delete=models.CASCADE)
    feature_name = models.CharField(max_length=150)
    feature_status = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_feature_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="subcription_feature_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.feature_name}"

    class Meta:
        db_table = "subscription_feature"


class SubscriptionInvoice(models.Model):
    INVOICE_CHOICES = ("Performa Invoice", "Performa Invoice"), (
        "Commercial Invoice",
        "Commercial Invoice",
    )
    invoice_number = models.CharField(max_length=50, null=True)
    invoice_date = models.DateField(null=True)
    due_date = models.DateField(null=True)
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.DO_NOTHING, null=True)
    subscription = models.ForeignKey(
        Subcription, on_delete=models.DO_NOTHING, null=True
    )
    invoice_type = models.CharField(
        max_length=50, choices=INVOICE_CHOICES, default="Performa Invoice"
    )
    quantity = models.FloatField(default=1)
    sell_price = models.FloatField(default=0)
    rate = models.FloatField(default=0)
    gst_rate = models.FloatField(default=18)
    amount = models.FloatField(default=0)
    note = models.TextField(null=True)
    sgst = models.FloatField(default=0)
    cgst = models.FloatField(default=0)
    total = models.FloatField(default=0)

    payment_reference_id = models.CharField(max_length=150, null=True)
    check_out_url = models.CharField(max_length=750, null=True)
    active = models.BooleanField(default=False, null=True)

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
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.invoice_number}-{self.invoice_date}-{self.company}"

    class Meta:
        db_table = "subscription_invoice"
        ordering = ["-id"]


class PurchasedSubscription(models.Model):
    PAYMENT_MODE_CHOICES = (
        ("NEFT", "NEFT"),
        ("RTGS", "RTGS"),
        ("IMPS", "IMPS"),
        ("UPI", "UPI"),
        ("Cheque", "Cheque"),
        ("Cash", "Cash"),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subcription, on_delete=models.CASCADE)
    duration = models.CharField(max_length=50)
    per_user_price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    sell_price = models.FloatField(default=0)
    payment_mode = models.CharField(
        max_length=100, choices=PAYMENT_MODE_CHOICES, default="Cheque"
    )
    payment_reference_id = models.CharField(max_length=150, null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchased_subscription_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchased_subscription_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.company}-{self.subscription}-{self.payment_mode}"

    class Meta:
        db_table = "purchased_subscription"
        ordering = ["-id"]


class PaymentSubscription(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subcription, on_delete=models.CASCADE)
    sell_price = models.FloatField(default=0)
    amount = models.FloatField(default=0.0)
    duration = models.CharField(max_length=50)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    check_out_url = models.URLField(blank=True, null=True)
    invoice_no = models.CharField(max_length=50, default="0")
    active = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Inactive")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    razor_order_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10, default="INR")

    def __str__(self):
        return f"Subscription {self.id} - {self.company.name}"  # type: ignore

    class Meta:
        db_table = "payment_subscription"
