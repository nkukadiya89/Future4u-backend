from django.conf import settings
from django.db import models
from django.utils.timezone import now

from country.models import Country


class Currency(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    currency_name = models.CharField(max_length=200)
    currency_code = models.CharField(max_length=200)
    currency_symbol = models.CharField(max_length=200)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.currency_name} - {self.currency_symbol}"

    class Meta:
        db_table = "currency"
