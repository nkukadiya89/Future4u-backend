from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError as DRFValidationError

from education_level.models import EducationLevel
from education_level.serializers import EducationLevelSerializer
from education_level.services import education_level_service


class EducationLevelAdminForm(forms.ModelForm):
    class Meta:
        model = EducationLevel
        exclude = ("deleted", "deleted_at", "deleted_by")

    def clean(self):
        cleaned = super().clean()
        min_age = cleaned.get("min_age")
        max_age = cleaned.get("max_age")
        if min_age is not None and max_age is not None and min_age > max_age:
            self.add_error("max_age", "max_age must be greater than or equal to min_age.")
        return cleaned


@admin.register(EducationLevel)
class EducationLevelAdmin(admin.ModelAdmin):
    form = EducationLevelAdminForm
    change_list_template = "admin/education_level/education_level/change_list.html"

    list_display = (
        "level_code",
        "display_name",
        "sequence_order",
        "min_age",
        "max_age",
        "is_active",
        "deleted",
        "created_at",
        "row_actions",
    )
    list_display_links = ("level_code", "display_name")
    search_fields = ("level_code", "display_name")
    list_filter = ("is_active", "deleted")
    ordering = ("sequence_order", "display_name")
    raw_id_fields = ("created_by", "updated_by")
    readonly_fields = ("created_by", "created_at", "updated_by", "updated_at", "deleted_at", "deleted_by")
    actions = (
        "activate_selected",
        "deactivate_selected",
        "archive_selected",
        "restore_selected",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "level_code",
                    "display_name",
                    "sequence_order",
                    "min_age",
                    "max_age",
                    "is_active",
                )
            },
        ),
        ("Archive/Restore", {"fields": ("deleted", "deleted_at", "deleted_by")}),
        (
            "Audit",
            {
                "fields": ("created_by", "created_at", "updated_by", "updated_at"),
            },
        ),
    )

    @admin.display(description="Actions")
    def row_actions(self, obj):
        token = getattr(self, "_csrf_token", "")
        return format_html(
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="education_level_admin_toggle_active" value="{}"/>'
            '<button type="submit" class="button">Toggle active</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="education_level_admin_archive_one" value="{}"/>'
            '<button type="submit" class="button">Archive</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="education_level_admin_restore_one" value="{}"/>'
            '<button type="submit" class="button">Restore</button></form>',
            token,
            str(obj.pk),
            token,
            str(obj.pk),
            token,
            str(obj.pk),
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
        data = education_level_service.sample_csv_bytes()
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="education_level_master_sample.csv"'
        return resp

    def upload_view(self, request):
        if request.method == "POST":
            f = request.FILES.get("file")
            rows, errs = education_level_service.parse_import_file(f)
            if not rows:
                self.message_user(
                    request,
                    " ".join(errs) if errs else "No rows to import.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(reverse("admin:education_level_educationlevel_upload"))
            result = education_level_service.bulk_import_levels(
                user=request.user,
                rows=rows,
                serializer_class=EducationLevelSerializer,
                context={"request": request},
            )
            self.message_user(
                request,
                f"Imported {result['success_count']}, failed {result['error_count']}.",
            )
            if result["error_details"][:5]:
                for d in result["error_details"][:5]:
                    self.message_user(
                        request,
                        f"Row {d['row']}: {d['message']}",
                        level=messages.WARNING,
                    )
            return HttpResponseRedirect(reverse("admin:education_level_educationlevel_changelist"))
        return render(request, "admin/education_level/education_level/upload_education_levels.html", {})

    def changelist_view(self, request, extra_context=None):
        self._csrf_token = get_token(request)
        if request.method == "POST":
            if request.POST.get("education_level_admin_toggle_active"):
                pk = request.POST["education_level_admin_toggle_active"]
                obj = EducationLevel.objects.filter(pk=pk).first()
                if obj:
                    education_level_service.set_active_status(
                        level=obj,
                        user=request.user,
                        is_active=not obj.is_active,
                    )
                    self.message_user(request, "Active status updated.")
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("education_level_admin_archive_one"):
                pk = request.POST["education_level_admin_archive_one"]
                obj = EducationLevel.objects.filter(pk=pk, deleted=False).first()
                if obj:
                    try:
                        education_level_service.archive_level(level=obj, user=request.user)
                        self.message_user(request, "Archived.")
                    except DRFValidationError as exc:
                        self.message_user(request, str(exc.detail), level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("education_level_admin_restore_one"):
                pk = request.POST["education_level_admin_restore_one"]
                obj = EducationLevel.objects.filter(pk=pk, deleted=True).first()
                if obj:
                    education_level_service.restore_level(level=obj, user=request.user)
                    self.message_user(request, "Restored.")
                return HttpResponseRedirect(request.get_full_path())
        extra_context = extra_context or {}
        extra_context["upload_url"] = reverse("admin:education_level_educationlevel_upload")
        extra_context["sample_csv_url"] = reverse("admin:education_level_educationlevel_sample_csv")
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)

    @admin.action(description="Activate selected")
    def activate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = education_level_service.bulk_set_active(ids=ids, user=request.user, is_active=True)
        self.message_user(request, f"{n} education level(s) activated.")

    @admin.action(description="Deactivate selected")
    def deactivate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = education_level_service.bulk_set_active(ids=ids, user=request.user, is_active=False)
        self.message_user(request, f"{n} education level(s) deactivated.")

    @admin.action(description="Archive selected (soft)")
    def archive_selected(self, request, queryset):
        for obj in queryset.filter(deleted=False):
            try:
                education_level_service.archive_level(level=obj, user=request.user)
            except DRFValidationError as exc:
                self.message_user(request, f"{obj}: {exc.detail}", level=messages.ERROR)

    @admin.action(description="Restore selected")
    def restore_selected(self, request, queryset):
        n = 0
        for obj in queryset.filter(deleted=True):
            education_level_service.restore_level(level=obj, user=request.user)
            n += 1
        self.message_user(request, f"{n} education level(s) restored.")
