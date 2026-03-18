from django.conf import settings
from django.db import models
from django.utils.timezone import now

from city.models import City
from company.models import Company
from country.models import Country
from end_client.models import EndClient
from partner_company.models import PartnerCompany
from state.models import State


# Business Setting Database Model
class BusinessSetting(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_business_setting",
        null=True,
    )

    partner_company = models.ForeignKey(
        PartnerCompany,
        on_delete=models.CASCADE,
        related_name="partner_company_business_setting",
        null=True,
    )

    end_client = models.ForeignKey(
        EndClient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="end_client_business_setting",
    )

    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_business_settings",
        help_text="User who created this business setting",
    )

    notifications = models.BooleanField(default=True)
    sgst = models.FloatField(default=0, null=True, blank=True)
    cgst = models.FloatField(default=0, null=True, blank=True)
    igst = models.FloatField(default=0, null=True, blank=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_country",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_state",
    )
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_city",
    )
    currency = models.CharField(max_length=5, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_setting_created",
    )
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_setting_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_setting_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.company}"

    class Meta:
        db_table = "business_setting"
