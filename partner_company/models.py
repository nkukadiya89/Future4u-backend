from django.conf import settings
from django.db import models


class PartnerCompany(models.Model):
    # Minimal schema to satisfy historical migrations.
    id = models.BigAutoField(primary_key=True)

    partner_company_logo = models.CharField(max_length=250, null=True, blank=True)
    gst_no = models.CharField(max_length=15, null=True, blank=True)
    company_name = models.CharField(max_length=50)
    person_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)

    # Address relations were present historically; keep them minimal.
    gst_address_country = models.ForeignKey(
        "country.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_gst_country",
    )
    gst_address_state = models.ForeignKey(
        "state.State",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_gst_state",
    )
    gst_address_city = models.ForeignKey(
        "city.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_gst_city",
    )
    gst_address_area = models.ForeignKey(
        "city_areas.CityArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_gst_area",
    )
    gst_address_building = models.CharField(max_length=150, null=True, blank=True)
    gst_address_landmark = models.CharField(max_length=100, null=True, blank=True)
    gst_address_pincode = models.IntegerField(null=True, blank=True)

    communication_address_country = models.ForeignKey(
        "country.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_comm_country",
    )
    communication_address_state = models.ForeignKey(
        "state.State",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_comm_state",
    )
    communication_address_city = models.ForeignKey(
        "city.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_comm_city",
    )
    communication_address_area = models.ForeignKey(
        "city_areas.CityArea",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="partner_company_comm_area",
    )
    communication_address_building = models.CharField(max_length=150, null=True, blank=True)
    communication_address_landmark = models.CharField(max_length=100, null=True, blank=True)
    communication_address_pincode = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=25, null=True, blank=True)
    is_active = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_updated"
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_deleted"
    )

    class Meta:
        db_table = "partner_company"

    def __str__(self):
        return self.company_name


class PartnerCompanyDocument(models.Model):
    # Minimal schema to satisfy historical migrations.
    id = models.BigAutoField(primary_key=True)

    partner_company = models.ForeignKey(
        PartnerCompany, on_delete=models.CASCADE, related_name="partner_company_documents"
    )
    document_title = models.CharField(max_length=50, null=True, blank=True)
    document_file = models.CharField(max_length=250, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_document_created"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_document_updated"
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="partner_company_document_deleted"
    )

    class Meta:
        db_table = "partner_company_document"

    def __str__(self):
        return f"{self.id} - {self.document_title}"

