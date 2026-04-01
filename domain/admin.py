from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError as DRFValidationError

from base.admin import BaseAdmin
from domain.models import Domain
from domain.serializers import DomainSerializer
from domain.services import domain_service


class DomainAdminForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")
        inst = self.instance if self.instance.pk else None
        try:
            domain_service.assert_no_circular_parent(domain=inst, parent=parent)
        except DRFValidationError as e:
            err = e.detail
            if isinstance(err, dict):
                for field, msgs in err.items():
                    fname = "parent" if field == "parent_id" else field
                    if isinstance(msgs, list):
                        self.add_error(fname, msgs[0] if msgs else "")
                    else:
                        self.add_error(fname, str(msgs))
            else:
                raise forms.ValidationError(str(err))
        return cleaned


@admin.register(Domain)
class DomainAdmin(BaseAdmin):
    form = DomainAdminForm
    change_list_template = "admin/domain/domain/change_list.html"

    list_display = (
        "domain_code",
        "domain_name",
        "parent",
        "is_active",
        "deleted",
        "interest_weight",
        "aptitude_weight",
        "personality_weight",
        "work_style_weight",
        "score_display",
        "created_at",
        "row_actions",
    )
    list_display_links = ("domain_code", "domain_name")
    search_fields = ("domain_code", "domain_name")
    list_filter = ("is_active", "deleted", "parent")
    list_select_related = ("parent",)
    ordering = ("-created_at",)
    raw_id_fields = ("parent", "created_by", "updated_by")
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
                    "domain_code",
                    "domain_name",
                    "parent",
                    "parent_acceptance_level",
                    "future_relevance_score",
                    "description",
                    (
                        "interest_weight",
                        "aptitude_weight",
                        "personality_weight",
                        "work_style_weight",
                    ),
                    "is_active",
                )
            },
        ),
        ("Archive", {"fields": ("deleted", "deleted_at", "deleted_by")}),
        (
            "Audit",
            {
                "fields": ("created_by", "created_at", "updated_by", "updated_at"),
            },
        ),
    )

    @admin.display(description="Score", ordering="future_relevance_score")
    def score_display(self, obj):
        return obj.future_relevance_score

    @admin.display(description="Actions")
    def row_actions(self, obj):
        token = getattr(self, "_csrf_token", "")
        return format_html(
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="domain_admin_toggle_active" value="{}"/>'
            '<button type="submit" class="button">Toggle active</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="domain_admin_archive_one" value="{}"/>'
            '<button type="submit" class="button">Archive</button></form> '
            '<form style="display:inline" method="post">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}"/>'
            '<input type="hidden" name="domain_admin_restore_one" value="{}"/>'
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
        data = domain_service.sample_csv_bytes()
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="domain_master_sample.csv"'
        return resp

    def upload_view(self, request):
        if request.method == "POST":
            f = request.FILES.get("file")
            rows, errs = domain_service.parse_import_file(f)
            if not rows:
                self.message_user(
                    request,
                    " ".join(errs) if errs else "No rows to import.",
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(reverse("admin:domain_domain_upload"))
            result = domain_service.bulk_import_domains(
                user=request.user,
                rows=rows,
                serializer_class=DomainSerializer,
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
            return HttpResponseRedirect(reverse("admin:domain_domain_changelist"))
        return render(request, "admin/domain/domain/upload_domains.html", {})

    def changelist_view(self, request, extra_context=None):
        self._csrf_token = get_token(request)
        if request.method == "POST":
            if request.POST.get("domain_admin_toggle_active"):
                pk = request.POST["domain_admin_toggle_active"]
                obj = Domain.objects.filter(pk=pk).first()
                if obj:
                    domain_service.set_active_status(
                        domain=obj,
                        user=request.user,
                        is_active=not obj.is_active,
                    )
                    self.message_user(request, "Active status updated.")
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("domain_admin_archive_one"):
                pk = request.POST["domain_admin_archive_one"]
                obj = Domain.objects.filter(pk=pk, deleted=False).first()
                if obj:
                    try:
                        domain_service.archive_domain(domain=obj, user=request.user)
                        self.message_user(request, "Archived.")
                    except DRFValidationError as exc:
                        self.message_user(
                            request, str(exc.detail), level=messages.ERROR
                        )
                return HttpResponseRedirect(request.get_full_path())
            if request.POST.get("domain_admin_restore_one"):
                pk = request.POST["domain_admin_restore_one"]
                obj = Domain.objects.filter(pk=pk, deleted=True).first()
                if obj:
                    domain_service.restore_domain(domain=obj, user=request.user)
                    self.message_user(request, "Restored.")
                return HttpResponseRedirect(request.get_full_path())
        extra_context = extra_context or {}
        extra_context["upload_url"] = reverse("admin:domain_domain_upload")
        extra_context["sample_csv_url"] = reverse("admin:domain_domain_sample_csv")
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)

    @admin.action(description="Activate selected")
    def activate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = domain_service.bulk_set_active(ids=ids, user=request.user, is_active=True)
        self.message_user(request, f"{n} domain(s) activated.")

    @admin.action(description="Deactivate selected")
    def deactivate_selected(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        n = domain_service.bulk_set_active(ids=ids, user=request.user, is_active=False)
        self.message_user(request, f"{n} domain(s) deactivated.")

    @admin.action(description="Archive selected (soft)")
    def archive_selected(self, request, queryset):
        for obj in queryset.filter(deleted=False):
            try:
                domain_service.archive_domain(domain=obj, user=request.user)
            except DRFValidationError as exc:
                self.message_user(request, f"{obj}: {exc.detail}", level=messages.ERROR)

    @admin.action(description="Restore selected")
    def restore_selected(self, request, queryset):
        n = 0
        for obj in queryset.filter(deleted=True):
            domain_service.restore_domain(domain=obj, user=request.user)
            n += 1
        self.message_user(request, f"{n} domain(s) restored.")
