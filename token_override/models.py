from django.conf import settings
from django.db import models


class TokenOverride(models.Model):
    """Extra monthly tokens granted by Super Admin per user or per entity."""

    ENTITY_TYPES = [
        ("school_college", "School / College"),
        ("institute", "Institute"),
        ("corporate", "Corporate"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="token_overrides",
    )
    entity_type = models.CharField(
        max_length=20,
        choices=ENTITY_TYPES,
        null=True,
        blank=True,
    )
    entity_user_id = models.IntegerField(
        null=True,
        blank=True,
    )

    extra_monthly_tokens = models.IntegerField(default=0)

    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="token_overrides_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="token_overrides_updated",
    )
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="token_overrides_deleted",
    )

    def __str__(self):
        if self.user:
            return f"User {self.user_id} +{self.extra_monthly_tokens}"
        if self.entity_type:
            return f"{self.entity_type} +{self.extra_monthly_tokens}"
        return f"TokenOverride #{self.id}"

    class Meta:
        db_table = "token_override"
        ordering = ["-created_at"]
