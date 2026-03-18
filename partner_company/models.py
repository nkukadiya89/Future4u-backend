from django.conf import settings
from django.db import models

from city.models import City
from city_areas.models import CityArea
from country.models import Country
from state.models import State
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class PartnerCompany(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )

    partner_company_logo = models.CharField(max_length=250, null=True)
    gst_no = models.CharField(max_length=15, null=True)
    company_name = models.CharField(max_length=50)
    person_name = models.CharField(max_length=150, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    gst_address_country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, related_name="partner_company_gst_country"
    )
    gst_address_state = models.ForeignKey(
        State, on_delete=models.SET_NULL, null=True, related_name="partner_company_gst_state"
    )
    gst_address_city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, related_name="partner_company_gst_city"
    )
    gst_address_building = models.CharField(max_length=150, null=True)
    gst_address_area = models.ForeignKey(
        CityArea, on_delete=models.SET_NULL, null=True, related_name="partner_company_gst_area"
    )
    gst_address_landmark = models.CharField(max_length=100, null=True)
    gst_address_pincode = models.IntegerField(null=True)

    communication_address_country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, related_name="partner_company_comm_country"
    )
    communication_address_state = models.ForeignKey(
        State, on_delete=models.SET_NULL, null=True, related_name="partner_company_comm_state"
    )
    communication_address_city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, related_name="partner_company_comm_city"
    )
    communication_address_building = models.CharField(max_length=150, null=True)
    communication_address_area = models.ForeignKey(
        CityArea, on_delete=models.SET_NULL, null=True, related_name="partner_company_comm_area"
    )
    communication_address_landmark = models.CharField(max_length=100, null=True)
    communication_address_pincode = models.IntegerField(null=True)

    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="partner_company_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="partner_company_updated",
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
        related_name="partner_company_deleted",
    )

    def __str__(self):
        return f"{self.company_name}"

    class Meta:
        db_table = "partner_company"

    def upload_partner_company_logo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.partner_company_logo:
            delete_uploaded_file(self.partner_company_logo)
        self.partner_company_logo, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "PartnerCompanyDocument/", self.id, None
        )


class PartnerCompanyDocument(models.Model):
    partner_company = models.ForeignKey(
        PartnerCompany, on_delete=models.CASCADE, related_name="partner_company_documents"
    )
    document_title = models.CharField(max_length=50, null=True)
    document_file = models.CharField(max_length=250, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="partner_company_document_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="partner_company_document_updated",
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
        related_name="partner_company_document_deleted",
    )

    def __str__(self):
        return f"{self.id} - {self.document_title}"

    class Meta:
        db_table = "partner_company_document"

    def upload_partner_company_document_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg", ".pdf"]
        if self.document_file:
            delete_uploaded_file(self.document_file)
        self.document_file, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "PartnerCompanyDocumentFile/", self.id, None  # type: ignore
        )
