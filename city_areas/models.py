from django.conf import settings
from django.db import models


class CityArea(models.Model):
    # Minimal schema to satisfy historical migrations.
    # The full city-areas app was removed from business logic.
    id = models.BigAutoField(primary_key=True)

    country = models.ForeignKey("country.Country", on_delete=models.SET_NULL, null=True, blank=True)
    state = models.ForeignKey("state.State", on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey("city.City", on_delete=models.SET_NULL, null=True, blank=True)

    city_area_name = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="city_area_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="city_area_updated"
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="city_area_deleted"
    )

    class Meta:
        db_table = "city_area"

    def __str__(self):
        return self.city_area_name or str(self.id)

