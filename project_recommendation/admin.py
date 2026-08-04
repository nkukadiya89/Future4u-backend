"""
Django admin for AI project recommendation (project_recommendation).

No database table; changelist is a live panel to test AI project generation.

URL: /admin/project_recommendation/projectrecommendationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from assessment.models import (
    ParentAssessment,
    ProfessionalAssessment,
    StudentAssessment,
)
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from ai.config import is_configured
from project_recommendation.exceptions import (
    ProjectRecommendationConfigurationError,
    ProjectRecommendationValidationError,
)
from project_recommendation.models import (
    ProjectRecommendation,
    ProjectRecommendationPanel,
)
from project_recommendation.services.project_service import ProjectRecommendationService
from user.models import User


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    from ai.config import llm_provider
    configured = is_configured()
    enabled = getattr(settings, "PROJECT_RECOMMENDATION_ENABLED", True)
    pname = llm_provider()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {pname} not configured"
    else:
        mode = f"{pname} project generation"
    return {
        "project_recommendation_enabled": enabled,
        "provider_name": pname,
        "provider_configured": configured,
        "ai_llm_enabled": configured,
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class ProjectRecommendationRunForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(deleted=False),
        required=True,
        empty_label="Select a user",
        help_text="Select the user to generate project recommendations for.",
    )
    assessment_id = forms.IntegerField(
        required=True,
        help_text="Required. Assessment ID to generate projects from.",
    )

    def clean_assessment_id(self):
        assessment_id = self.cleaned_data["assessment_id"]
        user = self.cleaned_data.get("user")
        
        if user and assessment_id:
            # Verify assessment exists and belongs to user
            assessment_models = [
                StudentAssessment,
                ParentAssessment,
                ProfessionalAssessment,
            ]
            found = False
            for ModelClass in assessment_models:
                try:
                    ModelClass.objects.get(
                        id=assessment_id,
                        user=user,
                        deleted=False,
                    )
                    found = True
                    break
                except ModelClass.DoesNotExist:
                    continue
            
            if not found:
                raise forms.ValidationError(
                    "Assessment not found or does not belong to the selected user."
                )
        
        return assessment_id


@admin.register(ProjectRecommendation)
class ProjectRecommendationAdmin(admin.ModelAdmin):
    """View/edit saved AI project recommendation responses."""

    list_display = (
        "id",
        "profile_type",
        "user",
        "assessment_link",
        "domain",
        "education_level",
        "token_usage",
        "last_recommended_at",
        "deleted",
        "created_at",
    )
    list_filter = ("profile_type", "deleted", "last_recommended_at", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "domain",
        "domain_category",
    )
    raw_id_fields = (
        "user",
        "student_assessment",
        "parent_assessment",
        "professional_assessment",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
        "raw_ai_response",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "profile_type",
                    "user",
                    "student_assessment",
                    "parent_assessment",
                    "professional_assessment",
                    "domain",
                    "domain_category",
                    "education_level",
                    "token_usage",
                    "last_recommended_at",
                    "deleted",
                )
            },
        ),
        (
            "AI payload",
            {
                "classes": ("collapse",),
                "fields": ("raw_ai_response",),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "user",
            "student_assessment",
            "parent_assessment",
            "professional_assessment",
        )

    @admin.display(description="Assessment")
    def assessment_link(self, obj):
        return (
            obj.student_assessment_id
            or obj.parent_assessment_id
            or obj.professional_assessment_id
        )


@admin.register(ProjectRecommendationPanel)
class ProjectRecommendationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = ProjectRecommendationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            user = form.cleaned_data.get("user")
            assessment_id = form.cleaned_data["assessment_id"]

            generation_input = {
                "user": user.pk if user else None,
                "user_email": user.email if user else "",
                "assessment_id": assessment_id,
            }

            diagnostics = {
                "requested_by": getattr(request.user, "email", ""),
                "provider": _provider_status(),
                "input": generation_input,
            }

            try:
                service = ProjectRecommendationService()
                data, token_usage = service.generate(
                    user=user,
                    assessment_id=assessment_id,
                )
                result = {
                    "data": data,
                    "token_usage": token_usage,
                }
            except ProjectRecommendationConfigurationError as exc:
                error = f"AI not configured: {exc}"
            except ProjectRecommendationValidationError as exc:
                error = f"AI generation failed ({exc.error}): {exc.details}"
            except Exception as exc:
                error = f"Unexpected error: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Project Recommendation",
            "form": form,
            "provider": _provider_status(),
            "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/project_recommendation/panel.html", context)
