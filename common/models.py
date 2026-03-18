from datetime import date

from django.conf import settings
from django.db import models
from django.utils.timezone import now


# Create your models here.
class FinancialYearModel(models.Model):
    fid = models.AutoField(primary_key=True)
    financial_year = models.CharField(max_length=15, default="")
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)
    approved_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"({self.fid} )"

    class Meta:
        db_table = "financial_year"
