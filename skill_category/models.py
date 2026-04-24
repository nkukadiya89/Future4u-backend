import os
from django.db import models
from common.models import BaseModule
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class SkillCategory(BaseModule):
    category_name = models.CharField(max_length=255, null=True, blank=True)
    category_image_url = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.category_name

    def upload_category_image(self, category_image_file):
        allowed_types = [".jpg", ".jpeg", ".png"]

        file_extension = os.path.splitext(category_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            raise ValueError(f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}.")

        current_value = getattr(self, "category_image_url", None)

        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, presigned_url = upload_file_to_bucket(
                category_image_file,
                allowed_types,
                "SkillCategory/",
                self.id,
                None,
            )
            self.category_image_url = aws_file_url
            self.save(update_fields=["category_image_url"])
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload category image: {str(e)}")

    class Meta:
        db_table = "skill_category"
        ordering = ["category_name"]