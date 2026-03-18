from django.db import models

from future4u import settings
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket

# Create your models here.


class Employee(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    alternate_mobile = models.CharField(max_length=15, null=True, blank=True)
    aadhar_card = models.CharField(max_length=20, null=True, blank=True)
    pan_card = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=15, null=True)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)
    profile_photo = models.CharField(max_length=150, null=True)

    permanent_address_building = models.CharField(max_length=255, null=True, blank=True)
    permanent_address_area = models.CharField(max_length=255, null=True, blank=True)
    permanent_address_landmark = models.CharField(max_length=255, null=True, blank=True)
    permanent_address_pincode = models.CharField(max_length=10, null=True, blank=True)
    permanent_address_country = models.CharField(max_length=100, null=True, blank=True)
    permanent_address_state = models.CharField(max_length=100, null=True, blank=True)
    permanent_address_city = models.CharField(max_length=100, null=True, blank=True)

    current_address_building = models.CharField(max_length=255, null=True, blank=True)
    current_address_area = models.CharField(max_length=255, null=True, blank=True)
    current_address_landmark = models.CharField(max_length=255, null=True, blank=True)
    current_address_pincode = models.CharField(max_length=10, null=True, blank=True)
    current_address_country = models.CharField(max_length=100, null=True, blank=True)
    current_address_state = models.CharField(max_length=100, null=True, blank=True)
    current_address_city = models.CharField(max_length=100, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employee_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="employee_updated",
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
        related_name="employee_deleted",
    )

    def __str__(self):
        return self.first_name

    class Meta:
        db_table = "employee"

    def upload_profile_photo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.profile_photo:
            delete_uploaded_file(self.profile_photo)
        self.profile_photo, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "EmployeeDocument/", self.id, None
        )
