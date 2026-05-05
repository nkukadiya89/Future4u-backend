from django.conf import settings
from django.db import models


class EndClient(models.Model):
    # Minimal schema to satisfy historical migrations.
    id = models.BigAutoField(primary_key=True)

    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    profile_photo = models.CharField(max_length=150, null=True, blank=True)

    status = models.CharField(max_length=25, null=True, blank=True)
    deleted = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="end_client_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="end_client_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="end_client_deleted",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "end_client"

    def __str__(self):
        return self.name or str(self.id)
