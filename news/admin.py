from django.contrib import admin
from django import forms

from .models import News


class NewsAdminForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Image")

    class Meta:
        model = News
        fields = ["title", "short_description", "content", "category", "image", "is_published"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.image:
            self.fields["image"].widget.attrs["readonly"] = True
            self.fields["image"].help_text = f"Current image: {self.instance.image}"

    def save(self, commit=True):
        instance = super().save(commit=False)
        image_file = self.cleaned_data.get("image_file")
        if image_file:
            if commit:
                instance.save()
            instance.upload_news_image(image_file)
        return instance


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    form = NewsAdminForm
    list_display = ("title", "category", "is_published", "published_at")
    search_fields = ("title", "content")
    readonly_fields = ("image",)
