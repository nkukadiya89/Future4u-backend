from django.conf import settings
from django.db import models
from django.utils.timezone import now
from company.models import Company

class Subscription(models.Model):
    SUBSCRIPTION_CHOICES = (
        ("subscription", "Subscription"),
        ("transfer", "Transfer"),
    )
    STATUS_CHOICES = (
        ("active", "active"),
        ("in_active", "in_active"),
    )
    package_name = models.CharField(max_length=100)
    subscription_type = models.CharField(max_length=50, choices=SUBSCRIPTION_CHOICES, default="subscription")
    device_price = models.FloatField(default=0)
    device_discount = models.FloatField(default=0)
    device_sell_price = models.FloatField(default=0)
    subscription_price = models.FloatField(default=0)
    subscription_discount = models.FloatField(default=0)
    subscription_sell_price = models.FloatField(default=0)
    plan_price = models.FloatField(default=0)
    # Transfer specific fields
    device_transfer_price = models.FloatField(default=0)
    device_transfer_discount = models.FloatField(default=0)
    device_transfer_sell_price = models.FloatField(default=0)
    duration_days = models.IntegerField(default=0)
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
        return f"{self.package_name}"

    class Meta:
        db_table = "subscription"


class SubscriptionFeature(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    feature_name = models.CharField(max_length=150)
    feature_status = models.BooleanField(default=False)
    is_core = models.BooleanField(default=False)

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
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.feature_name}"

    class Meta:
        db_table = "subscription_feature"


class SubscriptionCart(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True)
    quantity = models.IntegerField(default=1)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.subscription.package_name} x {self.quantity}"

    class Meta:
        db_table = "subscription_cart"


class PaymentSubscription(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Inactive", "Inactive"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    amount = models.FloatField(default=0.0)
    check_out_url = models.URLField(blank=True, null=True)
    invoice_no = models.CharField(max_length=50)
    active = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Inactive")
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default="pending")
    razor_order_id = models.CharField(max_length=100, blank=True, null=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=10)
    subtotal = models.FloatField(default=0)
    cgst_amount = models.FloatField(default=0)
    sgst_amount = models.FloatField(default=0)
    igst_amount = models.FloatField(default=0)
    total_amount = models.FloatField(default=0)
    payment_method = models.CharField(max_length=30, null=True, blank=True)
    payment_method_desc = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    is_renewal = models.BooleanField(default=False)

    def __str__(self):
        return f"Subscription {self.id} - {self.company.name}"

    class Meta:
        db_table = "payment_subscription"


class PaymentSubscriptionItem(models.Model):
    payment_subscription = models.ForeignKey(PaymentSubscription, on_delete=models.CASCADE, related_name="items")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    subscription_type = models.CharField(max_length=50)
    device_price = models.FloatField(default=0)
    subscription_price = models.FloatField(default=0)
    device_amount = models.FloatField(default=0)
    subscription_amount = models.FloatField(default=0)
    plan_total = models.FloatField(default=0)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "payment_subscription_item"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.payment_subscription.id} - {self.subscription.package_name}"


class PaymentGSTDetails(models.Model):
    payment_subscription = models.ForeignKey(PaymentSubscription, on_delete=models.CASCADE, related_name="gst_details")
    company_name = models.CharField(max_length=255)
    gst_no = models.CharField(max_length=15)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    building = models.CharField(max_length=255)
    area = models.CharField(max_length=255)
    landmark = models.CharField(max_length=255, null=True, blank=True)
    pincode = models.CharField(max_length=6)

    class Meta:
        db_table = "payment_gst_details"

    def __str__(self):
        return f"{self.company_name} - {self.gst_no}"


class SubscriptionInvoice(models.Model):
    INVOICE_CHOICES = ("Performa Invoice", "Performa Invoice"), (
        "Commercial Invoice",
        "Commercial Invoice",
    )
    invoice_number = models.CharField(max_length=50, null=True)
    invoice_date = models.DateField(null=True)
    due_date = models.DateField(null=True)
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, null=True)
    currency = models.CharField(max_length=10, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.DO_NOTHING, null=True)
    invoice_type = models.CharField(max_length=50, choices=INVOICE_CHOICES, default="Performa Invoice")
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
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.invoice_number}-{self.invoice_date}-{self.company}"

    class Meta:
        db_table = "subscription_invoice"
        ordering = ["-id"]


class SubscriptionCartWithSite(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="subscription_carts_with_site")
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="subscription_carts_with_site"
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"Cart {self.id} - {self.company.name} - {self.subscription.package_name}"

    class Meta:
        db_table = "subscription_cart_with_site"


class RenewalCart(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="renewal_carts")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "renewal_cart"

    def __str__(self):
        return f"{self.device_configuration.device_code} - Renewal Cart"
