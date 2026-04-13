from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from base.admin import BaseAdmin
from language_master.models import Language
from language_master.serializers import LanguageSerializer
from language_master.services import language_service


class LanguageAdminForm(forms.ModelForm):
    class Meta:
        model = Language
        fields = "__all__"

    def clean_code(self):
        value = (self.cleaned_data.get("code") or "").strip().upper()
        if not value:
            raise forms.ValidationError("Code may not be blank.")
        exclude_pk = self.instance.pk if self.instance and self.instance.pk else None
        if language_service.case_insensitive_code_exists(
            code=value, exclude_pk=exclude_pk
        ):
            raise forms.ValidationError(f"Language with code '{value}' already exists.")
        return value


@admin.register(Language)
class LanguageAdmin(BaseAdmin):
    form = LanguageAdminForm
    change_list_template = "admin/language_master/language/change_list.html"

    list_display = ("code", "name", "description", "is_active", "deleted", "created_at")
    list_display_links = ("code", "name")
    search_fields = ("code", "name")
    list_filter = ("is_active", "deleted")
    ordering = ("name",)
    readonly_fields = ("created_by", "created_at", "updated_by", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "code", "description", "is_active")}),
        ("Archive", {"fields": ("deleted", "deleted_at", "deleted_by")}),
        ("Audit", {"fields": ("created_by", "created_at", "updated_by", "updated_at")}),
    )

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "upload/",
                self.admin_site.admin_view(self.upload_view),
                name="%s_%s_upload" % info,
            ),
            path(
                "sample-csv/",
                self.admin_site.admin_view(self.sample_csv_view),
                name="%s_%s_sample_csv" % info,
            ),
        ] + super().get_urls()

    def sample_csv_view(self, request):
        data = language_service.sample_csv_bytes()
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = (
            'attachment; filename="language_master_sample.csv"'
        )
        return resp

    def upload_view(self, request):
        if request.method == "POST":
            f = request.FILES.get("file")
            rows, errs = language_service.parse_import_file(f)
            if not rows:
                self.message_user(
                    request,
                    " ".join(errs) if errs else "No rows to import.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(
                    reverse("admin:language_master_language_upload")
                )
            from user.models import User

            user = request.user
            result = language_service.bulk_import_languages(
                user=user,
                rows=rows,
                serializer_class=LanguageSerializer,
                context={"request": request},
            )
            self.message_user(
                request,
                f"Imported {result['success_count']}, failed {result['error_count']}.",
            )
            return HttpResponseRedirect(
                reverse("admin:language_master_language_changelist")
            )
        return render(
            request, "admin/language_master/language/upload_languages.html", {}
        )

    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)
