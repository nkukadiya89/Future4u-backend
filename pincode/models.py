from django.db import models
from django.utils.timezone import now

from future4u import settings
from utils.aws_file_upload import upload_file_to_bucket


class PinCode(models.Model):
    pincode_number = models.CharField(max_length=20)
    city_name = models.CharField(max_length=100, null=True)
    state_name = models.CharField(max_length=100, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pin_code_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pin_code_updated",
    )
    deleted = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.pincode_number}"

    class Meta:
        db_table = "pin_code"

    def upload_presentation(self, file_to_upload):
        allowed_type = [".jpg", ".png", ".jpeg", ".csv"]
        self.upload_csv, presigned_url = upload_file_to_bucket(
            file_to_upload, allowed_type, "UploadCsv/", self.id, None  # type: ignore
        )
