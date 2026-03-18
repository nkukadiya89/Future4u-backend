from django.conf import settings
from django.db import models

from business_category.models import BusinessCategory
from city.models import City
from city_areas.models import CityArea
from country.models import Country
from state.models import State
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket

# Create your models here.


class Company(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )
    COMPANY_TYPE = (("Media owner", "Media owner"), ("Advertisers", "Advertisers"))
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

    # Required fields only
    company_logo = models.CharField(max_length=250, null=True)
    gst_no = models.CharField(max_length=15, null=True)
    name = models.CharField(max_length=50)
    business_category = models.ForeignKey(
        BusinessCategory, on_delete=models.CASCADE, related_name="companies", null=True
    )
    person_name = models.CharField(max_length=150, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company_type = models.CharField(choices=COMPANY_TYPE, max_length=25, null=True, blank=True)
    gst_no_verified = models.BooleanField(default=False)

    gst_address_country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, related_name="gst_address_companies"
    )
    gst_address_state = models.ForeignKey(
        State, on_delete=models.SET_NULL, null=True, related_name="gst_address_companies"
    )
    gst_address_city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, related_name="gst_address_companies"
    )
    gst_address_building = models.CharField(max_length=150, null=True)
    gst_address_area = models.ForeignKey(
        CityArea, on_delete=models.SET_NULL, null=True, related_name="gst_address_companies"
    )
    gst_address_landmark = models.CharField(max_length=100, null=True)
    gst_address_pincode = models.IntegerField(null=True)

    communication_address_country = models.ForeignKey(
        Country, on_delete=models.SET_NULL, null=True, related_name="communication_address_companies"
    )
    communication_address_state = models.ForeignKey(
        State, on_delete=models.SET_NULL, null=True, related_name="communication_address_companies"
    )
    communication_address_city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, related_name="communication_address_companies"
    )
    communication_address_building = models.CharField(max_length=150, null=True)
    communication_address_area = models.ForeignKey(
        CityArea, on_delete=models.SET_NULL, null=True, related_name="communication_address_companies"
    )
    communication_address_landmark = models.CharField(max_length=100, null=True)
    communication_address_pincode = models.IntegerField(null=True)

    secondary_email = models.EmailField(null=True, blank=True)
    secondary_phone = models.CharField(max_length=20, null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)
    pinterest_url = models.URLField(null=True, blank=True)
    year_of_establishment = models.IntegerField(default=0000)
    number_of_employees = models.CharField(choices=EMPLOYEES_CHOICES, default="1-10 employees", max_length=25)
    monday_friday_hours = models.CharField(max_length=50, null=True, blank=True)
    saturday_hours = models.CharField(max_length=50, null=True, blank=True)
    sunday_hours = models.CharField(max_length=50, null=True, blank=True)
    services = models.ManyToManyField("CompanyService", related_name="companies")
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)
    is_active = models.BooleanField(default=False)
    active_subscription = models.BooleanField(default=False)
    expiry_date = models.DateField(null=True, blank=True)
    days_to_expire = models.IntegerField(default=0)
    is_request_demo = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="company_updated",
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
        related_name="company_deleted",
    )

    def __str__(self):
        return f"{self.name}"

    def upload_company_logo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.company_logo:
            delete_uploaded_file(self.company_logo)
        self.company_logo, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "CompanyDocument/", self.id, None
        )


class CompanyService(models.Model):
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "company_service"


class CompanyPhoto(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_photo", default=None)
    title = models.CharField(max_length=50, null=True)
    photo_file = models.CharField(max_length=250, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_photo_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_photo_updated",
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
        related_name="company_photo_deleted",
    )

    def __str__(self):
        return f"{self.id} - {self.title}"

    class Meta:
        db_table = "company_photo"

    def upload_company_photo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg", ".pdf"]
        if self.photo_file:
            delete_uploaded_file(self.photo_file)
        self.photo_file, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "CompanyPhoto/", self.id, None  # type: ignore
        )


class Enquiry(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    message = models.TextField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enquiries",
    )
    send_enquiry_to = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enquiries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"

    class Meta:
        db_table = "enquiry"
