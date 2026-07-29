from django import forms
from django.contrib import admin

from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "published_at")
    search_fields = ("title", "content")

    def save_model(self, request, obj, form, change):
        # Handle image upload to S3 before saving
        image_file = form.cleaned_data.get("image")
        if image_file and hasattr(image_file, "file"):
            # Upload to S3 first
            try:
                # Temporarily set image to None to prevent Django from saving it locally
                obj.image = None
                super().save_model(request, obj, form, change)
                # Now upload to S3
                s3_url = obj.upload_image_to_s3(image_file)
                obj.image.name = s3_url
                obj.save(update_fields=["image"])
            except Exception as e:
                raise forms.ValidationError(f"Failed to upload image to S3: {str(e)}")
        else:
            super().save_model(request, obj, form, change)
