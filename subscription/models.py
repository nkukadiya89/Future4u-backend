from django.conf import settings
from django.db import models
from django.utils.timezone import now

from base.models import BaseModel
from company.models import Company
from user.models import User


class AccessType(models.TextChoices):
    FULL = "full", "Full"
    LIMITED = "limited", "Limited"


class Subscription(BaseModel):
    package_name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    no_of_profile_assessment = models.IntegerField(default=0)
    no_of_tokens = models.IntegerField(default=0)

    internship_access_type = models.CharField(
        max_length=10, choices=AccessType.choices, default=AccessType.FULL
    )
    no_of_internship_access = models.IntegerField(null=True, blank=True, default=None)

    job_portal_access_type = models.CharField(
        max_length=10, choices=AccessType.choices, default=AccessType.FULL
    )
    no_of_job_portal_access = models.IntegerField(null=True, blank=True, default=None)

    course_portal_access_type = models.CharField(
        max_length=10, choices=AccessType.choices, default=AccessType.FULL
    )
    no_of_course_portal_access = models.IntegerField(null=True, blank=True, default=None)

    project_topic_access_type = models.CharField(
        max_length=10, choices=AccessType.choices, default=AccessType.FULL
    )
    no_of_project_topic_access = models.IntegerField(null=True, blank=True, default=None)

    career_compare = models.BooleanField(default=False)
    career_roadmap = models.BooleanField(default=False)
    ai_chat_access = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.package_name

    def clean(self):
        """Validate access type + count pairs."""
        from django.core.exceptions import ValidationError

        pairs = [
            ("internship_access_type", "no_of_internship_access", "Internship"),
            ("job_portal_access_type", "no_of_job_portal_access", "Job Portal"),
            ("course_portal_access_type", "no_of_course_portal_access", "Course Portal"),
            ("project_topic_access_type", "no_of_project_topic_access", "Project Topic"),
        ]
        for type_field, count_field, label in pairs:
            access_type = getattr(self, type_field, AccessType.FULL)
            count_val = getattr(self, count_field, None)
            if access_type == AccessType.LIMITED:
                if count_val is None or count_val <= 0:
                    raise ValidationError(
                        f"Count is required for {label} when access type is 'limited'."
                    )
            elif access_type == AccessType.FULL:
                if count_val is not None:
                    setattr(self, count_field, None)


class SubscriptionPlan(Subscription):
    """Backward-compatible logical plan.

    `Subscription` previously held pricing fields; we keep that model name
    but introduce `SubscriptionPlan` as explicit alias/extension for clarity.
    """

    class Meta:
        proxy = True


class PlanPrice(models.Model):
    PERIOD_CHOICES = (("monthly", "Monthly"), ("yearly", "Yearly"))

    plan = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="prices"
    )
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    price = models.IntegerField()
    duration_days = models.IntegerField()
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="planprice_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="planprice_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planprice_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.plan.package_name} - {self.period} - {self.price}"

    class Meta:
        ordering = ["-created_at"]


class SubscriptionFeature(models.Model):
    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="features"
    )
    feature_name = models.CharField(
        max_length=150, verbose_name="Feature Name", null=True, blank=True
    )
    feature_code = models.CharField(
        max_length=50, verbose_name="Unique code for feature", null=True, blank=True
    )
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
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.subscription.package_name} - {self.feature_name}"

    class Meta:
        ordering = ["-created_at"]


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # Link to the specific priced offer the user purchased (periodic price)
    # e.g. monthly or yearly PlanPrice
    plan_price = models.ForeignKey(
        "PlanPrice", on_delete=models.CASCADE, null=True, blank=True
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)
    # Tracks when monthly tokens were last reset for this user.
    # Used by check_token_available to enforce per-month windows for Pro plan.
    last_reset_at = models.DateField(null=True, blank=True)

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
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # UserSubscription is linked to a user and a subscription
        plan_name = None
        if self.plan_price and self.plan_price.plan:
            plan_name = self.plan_price.plan.package_name
        return f"{getattr(self.user, 'first_name', '') or getattr(self.user, 'email', '')} - {plan_name or ''}"

    def consume(self, feature_code, quantity=1):
        """Consume `quantity` of `feature_code` for the user using atomic service.

        Raises Exception if limit exceeded or no active subscription.
        """
        from subscription.services.usage import consume_feature

        if not self.is_active:
            raise Exception("Subscription not active")

        return consume_feature(self.user, feature_code, quantity)

    class Meta:
        ordering = ["-start_date"]


class FeatureUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feature_code = models.CharField(max_length=50)

    used = models.IntegerField(default=0)

    # Track usage against a specific purchase price/period (PlanPrice)
    plan_price = models.ForeignKey(
        "PlanPrice", on_delete=models.CASCADE, null=True, blank=True
    )

    last_used_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="feature_usage_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="feature_usage_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feature_usage_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{getattr(self.user, 'first_name', '') or getattr(self.user, 'email', '')} - {self.feature_code} - {self.used}"

    class Meta:
        ordering = ["-last_used_at"]


class PaymentSubscription(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    # Reference the exact priced offer bought (PlanPrice). Keep price snapshots
    # (amount, final_amount) for immutable history.
    plan_price = models.ForeignKey(
        "PlanPrice", on_delete=models.SET_NULL, null=True, blank=True
    )

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
    promocode = models.CharField(max_length=25, null=True, blank=True)

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
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        plan_name = None
        if self.plan_price and self.plan_price.plan:
            plan_name = self.plan_price.plan.package_name
        return f"{plan_name or 'Subscription'} - {self.final_amount} - {self.status}"

    class Meta:
        ordering = ["-created_at"]


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
    subscription = models.ForeignKey(
        "PlanPrice", on_delete=models.SET_NULL, null=True, blank=True
    )

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
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.invoice_number or 'Proforma'}"

    class Meta:
        ordering = ["-created_at"]


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
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]


class PromoCode(models.Model):
    code = models.CharField(max_length=25, unique=True)

    discount_type = models.CharField(
        choices=[("percent", "Percent"), ("flat", "Flat")], max_length=10
    )
    value = models.FloatField()

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, null=True, blank=True
    )

    is_active = models.BooleanField(default=True)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    usage_limit = models.IntegerField(null=True, blank=True)
    used_count = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="promo_code_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="promo_code_updated",
    )
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_code_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table = "promo_code"
        ordering = ["-created_at"]
