"""
Django admin for Resume Builder.

No database models — this admin page provides a live panel
to generate/preview a resume PDF for any user directly from admin.

URL:  /admin/resume_builder/resumebuilder/
"""

from django.contrib import admin, messages
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse

from common.mixins.admin_mixins import ReadOnlyAdminMixin

# ── Unmanaged proxy model (no DB table needed) ───────────────────────────────


class ResumeBuilder(models.Model):
    """Fake unmanaged model — only used to hook into Django admin."""

    class Meta:
        app_label = "resume_builder"
        managed = False  # no migration, no DB table
        verbose_name = "Resume Builder"
        verbose_name_plural = "Resume Builder"


# ── Admin class ───────────────────────────────────────────────────────────────


@admin.register(ResumeBuilder)
class ResumeBuilderAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):

    # ── Custom URLs ───────────────────────────────────────────────────────────
    def get_urls(self):
        custom = [
            path(
                "generate/<int:user_id>/",
                self.admin_site.admin_view(self.generate_view),
                name="resume_builder_resumebuilder_generate",
            ),
            path(
                "preview/<int:user_id>/",
                self.admin_site.admin_view(self.preview_view),
                name="resume_builder_resumebuilder_preview",
            ),
        ]
        return custom + super().get_urls()

    # ── Changelist = custom panel ─────────────────────────────────────────────
    def changelist_view(self, request, extra_context=None):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        users = (
            User.objects.filter(
                user_type__in=["student", "working_professional"], is_active=True
            )
            .select_related("country", "states", "city")
            .order_by("user_type", "first_name")[:200]
        )

        rows = []
        for u in users:
            rows.append(
                {
                    "id": u.id,
                    "name": u.full_name or u.email,
                    "email": u.email,
                    "role": u.user_type,
                    "gen_professional": reverse(
                        "admin:resume_builder_resumebuilder_generate", args=[u.id]
                    )
                    + "?template=professional",
                    "gen_standard": reverse(
                        "admin:resume_builder_resumebuilder_generate", args=[u.id]
                    )
                    + "?template=standard",
                    "preview": reverse(
                        "admin:resume_builder_resumebuilder_preview", args=[u.id]
                    ),
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "title": "Resume Builder",
            "users": rows,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),  # breadcrumb compat
        }
        return render(
            request, "admin/resume_builder/resume_builder_panel.html", context
        )

    # ── Generate PDF view ─────────────────────────────────────────────────────
    def generate_view(self, request, user_id):
        from django.contrib.auth import get_user_model

        from resume_builder.services import (
            build_professional_resume_data,
            build_student_resume_data,
            generate_resume_pdf,
        )
        from resume_builder.views import _get_profile

        User = get_user_model()
        try:
            user = User.objects.select_related("country", "states", "city").get(
                pk=user_id
            )
        except User.DoesNotExist:
            messages.error(request, f"User {user_id} not found.")
            return self._redirect_panel()

        template = request.GET.get("template", "professional")
        profile, resume_type = _get_profile(user)

        if resume_type is None:
            messages.error(
                request, f"{user.email} — role '{user.user_type}' is not supported."
            )
            return self._redirect_panel()

        if profile is None:
            messages.error(
                request,
                f"{user.email} — profile not found. Ask them to complete their profile.",
            )
            return self._redirect_panel()

        try:
            if resume_type == "fresher":
                data = build_student_resume_data(profile, user, template=template)
            else:
                data = build_professional_resume_data(profile, user, template=template)
            pdf_bytes = generate_resume_pdf(data)
        except ValueError as exc:
            messages.error(request, f"Resume generation failed: {exc}")
            return self._redirect_panel()
        except Exception as exc:
            messages.error(request, f"Unexpected error: {exc}")
            return self._redirect_panel()

        name = (user.full_name or user.email).replace(" ", "_")
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{name}_{template}_resume.pdf"'
        )
        return response

    # ── Preview JSON view ─────────────────────────────────────────────────────
    def preview_view(self, request, user_id):
        from django.contrib.auth import get_user_model

        from resume_builder.services import (
            build_professional_resume_data,
            build_student_resume_data,
        )
        from resume_builder.views import _get_profile

        User = get_user_model()
        try:
            user = User.objects.select_related("country", "states", "city").get(
                pk=user_id
            )
        except User.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": f"User {user_id} not found."}, status=404
            )

        template = request.GET.get("template", "professional")
        profile, resume_type = _get_profile(user)

        if resume_type is None:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Role '{user.user_type}' is not supported.",
                },
                status=400,
            )

        if profile is None:
            return JsonResponse(
                {"success": False, "message": "Profile not found."}, status=404
            )

        if resume_type == "fresher":
            data = build_student_resume_data(profile, user, template=template)
        else:
            data = build_professional_resume_data(profile, user, template=template)

        return JsonResponse({"success": True, "data": data})

    # ── Helper ────────────────────────────────────────────────────────────────
    def _redirect_panel(self):
        from django.http import HttpResponseRedirect

        return HttpResponseRedirect(
            reverse("admin:resume_builder_resumebuilder_changelist")
        )
