from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError as DRFValidationError

from base.admin import BaseAdmin
from skill.models import Skill
from skill.serializers import SkillSerializer
from skill.services import skill_service


@admin.register(Skill)
class SkillAdmin(BaseAdmin):
    change_list_template = "admin/skill/skill/change_list.html"

    list_display = (
        "skill_code",
        "skill_name",
        "skill_type",
        "is_active",
        "is_archived",
        "created_at",
        "row_actions",
    )
    list_display_links = ("skill_code", "skill_name")
    search_fields = ("skill_code", "skill_name")
    list_filter = ("skill_type", "is_active", "is_archived")
    ordering = ("skill_name",)
    raw_id_fields = ("created_by", "updated_by")
    readonly_fields = ("created_by", "created_at", "updated_by", "updated_at")
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
                    "skill_code",
                    "skill_name",
                    "skill_type",
                    "description",
                    "is_active",
                )
            },
        ),
        ("Archive", {"fields": ("is_archived",)}),
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
            '<input type="hidden" name="skill_admin_toggle_active" value="{}"/>'
            '<button type="submit" class="button">Toggle active</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="skill_admin_archive_one" value="{}"/>'
            '<button type="submit" class="button">Archive</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="skill_admin_restore_one" value="{}"/>'
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
        data = skill_service.sample_csv_bytes()
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="skill_master_sample.csv"'
        return resp

    def upload_view(self, request):
        if request.method == "POST":
            f = request.FILES.get("file")
            rows, errs = skill_service.parse_import_file(f)
            if not rows:
                self.message_user(
                    request,
                    " ".join(errs) if errs else "No rows to import.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(reverse("admin:skill_skill_upload"))
            result = skill_service.bulk_import_skills(
                user=request.user,
                rows=rows,
                serializer_class=SkillSerializer,
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
            return HttpResponseRedirect(reverse("admin:skill_skill_changelist"))
        return render(request, "admin/skill/skill/upload_skills.html", {})

    def changelist_view(self, request, extra_context=None):
        self._csrf_token = get_token(request)
        if request.method == "POST":
            if request.POST.get("skill_admin_toggle_active"):
                pk = request.POST["skill_admin_toggle_active"]
                obj = Skill.objects.filter(pk=pk).first()
                if obj:
                    skill_service.set_active_status(
                        skill=obj,
                        user=request.user,
                        is_active=not obj.is_active,
                    )
                    self.message_user(request, "Active status updated.")
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("skill_admin_archive_one"):
                pk = request.POST["skill_admin_archive_one"]
                obj = Skill.objects.filter(pk=pk, is_archived=False).first()
                if obj:
                    try:
                        skill_service.archive_skill(skill=obj, user=request.user)
                        self.message_user(request, "Archived.")
                    except DRFValidationError as exc:
                        self.message_user(request, str(exc.detail), level=messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("skill_admin_restore_one"):
                pk = request.POST["skill_admin_restore_one"]
                obj = Skill.objects.filter(pk=pk, is_archived=True).first()
                if obj:
                    skill_service.restore_skill(skill=obj, user=request.user)
                    self.message_user(request, "Restored.")
                return HttpResponseRedirect(request.get_full_path())
        extra_context = extra_context or {}
        extra_context["upload_url"] = reverse("admin:skill_skill_upload")
        extra_context["sample_csv_url"] = reverse("admin:skill_skill_sample_csv")
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)

    @admin.action(description="Activate selected")
    def activate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = skill_service.bulk_set_active(ids=ids, user=request.user, is_active=True)
        self.message_user(request, f"{n} skill(s) activated.")

    @admin.action(description="Deactivate selected")
    def deactivate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = skill_service.bulk_set_active(ids=ids, user=request.user, is_active=False)
        self.message_user(request, f"{n} skill(s) deactivated.")

    @admin.action(description="Archive selected (soft)")
    def archive_selected(self, request, queryset):
        for obj in queryset.filter(is_archived=False):
            try:
                skill_service.archive_skill(skill=obj, user=request.user)
            except DRFValidationError as exc:
                self.message_user(request, f"{obj}: {exc.detail}", level=messages.ERROR)

    @admin.action(description="Restore selected")
    def restore_selected(self, request, queryset):
        n = 0
        for obj in queryset.filter(is_archived=True):
            skill_service.restore_skill(skill=obj, user=request.user)
            n += 1
        self.message_user(request, f"{n} skill(s) restored.")

