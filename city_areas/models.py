from django.conf import settings
from django.db import models

from city.models import City
from country.models import Country
from state.models import State


class CityArea(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="city_areas_country")
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="city_areas_state")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="city_areas_city")
    city_area_name = models.CharField(max_length=255)
    zipcode = models.CharField(max_length=20)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="city_area_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="city_area_updated",
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
        related_name="city_area_deleted",
    )

    def __str__(self):
        return f"{self.city_area_name} - {self.zipcode} ({self.city.name}, {self.state.name}, {self.country.name})"

    class Meta:
        db_table = "city_area"
