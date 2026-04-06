from django.conf import settings
from django.db import models

from country.models import Country
from state.models import State


# Create your models here.
class City(models.Model):
    name = models.CharField(max_length=200)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="city_set"
    )
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="city_set")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="city_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="city_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="city_deleted",
    )

    def __str__(self):
        return f"{self.name}({self.country.name})({self.state.name})"

    class Meta:
        db_table = "city"
