from django.conf import settings
from django.db import models
from django.utils.timezone import now

from pincode.models import PinCode
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket

# Create your models here.


class Company(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )
    EMPLOYEES_CHOICES = (
        ("1-10 employees", "1-10 employees"),
        ("11-50 employees", "11-50 employees"),
        ("51-200 employees", "51-200 employees"),
        ("201-500 employees", "201-500 employees"),
        ("501-1000 employees", "501-1000 employees"),
        ("1001-5000 employees", "1001-5000 employees"),
        ("5001-10000 employees", "5001-10000 employees"),
        ("10000 + employees", "10000 + employees"),
    )
    COMPANY_TYPE = (("Buyer", "Buyer"), ("Seller", "Seller"))
    name = models.CharField(max_length=50)
    website = models.CharField(max_length=100, null=True)
    no_of_employees = models.CharField(
        choices=EMPLOYEES_CHOICES, default="1-10 employees", max_length=25, null=True
    )
    company_type = models.CharField(
        choices=COMPANY_TYPE, default="Buyer", max_length=25
    )
    company_pan = models.CharField(max_length=10, null=True)
    company_pan_verified = models.BooleanField(default=False)
    gst_no = models.CharField(max_length=15, null=True)
    gst_no_verified = models.BooleanField(default=False)
    about_company = models.TextField(null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    first_name = models.CharField(max_length=150, null=True)
    designation = models.CharField(max_length=150, null=True)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)
    is_active = models.BooleanField(default=False)
    unique_code = models.CharField(max_length=50, null=True)
    cin_no = models.CharField(max_length=50, null=True)
    risk_and_compliance_title = models.BooleanField(default=False)
    udhyam_aadharcard = models.CharField(max_length=100, null=True)
    udhyam_aadharcard_verified = models.BooleanField(default=False)

    registered_business_address_building = models.CharField(max_length=150, null=True)
    registered_business_address_area = models.CharField(max_length=100, null=True)
    registered_business_address_landmark = models.CharField(max_length=100, null=True)
    registered_business_address_state = models.CharField(max_length=100, null=True)
    registered_business_address_city = models.CharField(max_length=100, null=True)
    registered_business_address_pincode = models.ForeignKey(
        PinCode,
        on_delete=models.CASCADE,
        related_name="company_registered_business_address_pincode",
        null=True,
    )

    trading_address_building = models.CharField(max_length=150, null=True)
    trading_address_area = models.CharField(max_length=100, null=True)
    trading_address_landmark = models.CharField(max_length=100, null=True)
    trading_address_state = models.CharField(max_length=100, null=True)
    trading_address_city = models.CharField(max_length=100, null=True)
    trading_address_pincode = models.ForeignKey(
        PinCode,
        on_delete=models.CASCADE,
        related_name="company_trading_address_pincode",
        null=True,
    )
    active_subscription = models.BooleanField(default=False)
    expiry_date = models.DateField(null=True, blank=True)
    days_to_expire = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "company"
        indexes = [
            models.Index(fields=["deleted", "status"], name="company_del_status_idx"),
            models.Index(fields=["created_at"], name="company_created_at_idx"),
            models.Index(fields=["updated_at"], name="company_updated_at_idx"),
            models.Index(fields=["expiry_date"], name="company_expiry_date_idx"),
        ]

    def upload_company_logo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.company_logo:
            delete_uploaded_file(self.company_logo)
        self.company_logo, presigned_url = upload_file_to_bucket(
            file_to_upload,
            allowed_type,
            "CompanyDocument/",
            self.id,  # type: ignore
            None,
        )


class KeyPersons(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="key_person"
    )
    person_name = models.CharField(max_length=50, null=True)
    designation = models.CharField(max_length=50, null=True)
    email = models.EmailField(null=True)
    contact_number = models.CharField(max_length=15, null=True)
    department = models.CharField(max_length=100, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="keyperson_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="keyperson_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.id}{self.person_name}"  # type: ignore

    class Meta:
        db_table = "key_persons"
        indexes = [
            models.Index(
                fields=["company", "deleted"], name="keypersons_company_del_idx"
            ),
            models.Index(fields=["created_at"], name="keypersons_created_at_idx"),
        ]


class Attachment(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="attachment"
    )
    attachment_name = models.CharField(max_length=50, null=True)
    attachment_file = models.CharField(max_length=250, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="attachment_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="attachment_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.id}{self.attachment_name}"  # type: ignore

    class Meta:
        db_table = "attachment"
        indexes = [
            models.Index(
                fields=["company", "deleted"], name="attachment_company_del_idx"
            ),
            models.Index(fields=["created_at"], name="attachment_created_at_idx"),
        ]

    def upload_company_attachment_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg", ".pdf"]
        if self.attachment_file:
            delete_uploaded_file(self.attachment_file)
        self.attachment_file, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "AttachmentFile/", self.id, None  # type: ignore
        )


class CompanyEmail(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="company_email"
    )
    email = models.EmailField(null=True)
    person_name = models.CharField(max_length=50)
    designation = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=50)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_email_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_email_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.id} - {self.person_name}"  # type: ignore

    class Meta:
        db_table = "company_email"
        indexes = [
            models.Index(
                fields=["company", "deleted"], name="companyemail_company_del_idx"
            ),
            models.Index(fields=["created_at"], name="companyemail_created_at_idx"),
        ]


class CompanyProfile(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="company_percentage"
    )
    company_perc = models.IntegerField(default=0)
    company_material_perc = models.IntegerField(default=0)
    site_location_perc = models.IntegerField(default=0)
    user_role_perc = models.IntegerField(default=0)
    employee_perc = models.IntegerField(default=0)
    pr_release_perc = models.IntegerField(default=0)
    business_setting_perc = models.IntegerField(default=0)
    vendor_perc = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.company.name} - {self.id}"  # type: ignore

    class Meta:
        db_table = "company_profile"
        indexes = [
            models.Index(fields=["company"], name="companyprofile_company_idx"),
        ]
