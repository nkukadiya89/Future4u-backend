from django.conf import settings
from django.db import models

from country.models import Country


# Create your models here.
class State(models.Model):
    name = models.CharField(max_length=200)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="state_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="state_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="state_deleted",
    )

    def __str__(self):
        return f"{self.name}({self.country.name})"

    class Meta:
        db_table = "state"
