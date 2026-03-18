from django.conf import settings
from django.db import models
from django.utils.timezone import now


class Country(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=50, unique=True)
    unicode = models.CharField(max_length=80, unique=True)
    country_flag = models.URLField(max_length=200)
    phone_code = models.CharField(max_length=5, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="country_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="country_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "country"
