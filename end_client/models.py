from django.conf import settings
from django.db import models

from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


# Create your models here.
class EndClient(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    profile_photo = models.CharField(max_length=150, null=True)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="end_client_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="end_client_updated",
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
        related_name="end_client_deleted",
    )

    def __str__(self):
        return self.first_name

    class Meta:
        db_table = "end_client"

    def upload_profile_photo_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg"]

        if self.profile_photo:
            delete_uploaded_file(self.profile_photo)
        self.profile_photo, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "EndClientDocument/", self.id, None
        )
