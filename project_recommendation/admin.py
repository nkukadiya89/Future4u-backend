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

from ai.config import is_configured
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from domain.models import Domain
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
        mode = f"ai mode, {pname} not configured"
    else:
        mode = f"ai mode ({pname} project generation)"
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
    domain_category = forms.ModelChoiceField(
        queryset=Domain.objects.filter(deleted=False, parent__isnull=True),
        required=True,
        empty_label="Select Category (Root Domain)",
        help_text="Select domain category.",
    )
    domain = forms.ModelChoiceField(
        queryset=Domain.objects.filter(deleted=False, parent__isnull=False),
        required=True,
        empty_label="Select Domain (Child)",
        help_text="Select child domain under the category.",
    )
    overview = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="Optional project overview description.",
    )

    def clean(self):
        cleaned_data = super().clean()
        domain_obj = cleaned_data.get("domain")
        category_obj = cleaned_data.get("domain_category")

        if domain_obj and category_obj:
            if domain_obj.parent_id and str(domain_obj.parent_id) != str(category_obj.id):
                raise forms.ValidationError(
                    "Selected Domain does not belong to the selected Domain Category."
                )

        return cleaned_data



@admin.register(ProjectRecommendation)
class ProjectRecommendationAdmin(admin.ModelAdmin):
    """View/edit saved AI project recommendation responses."""

    list_display = (
        "id",
        "profile_type",
        "user",
        "domain",
        "domain_category",
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
        "overview",
    )
    raw_id_fields = ("user",)
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
                    "domain",
                    "domain_category",
                    "overview",
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
        return super().get_queryset(request).select_related("user")


@admin.register(ProjectRecommendationPanel)
class ProjectRecommendationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = ProjectRecommendationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            user = form.cleaned_data.get("user")
            domain_obj = form.cleaned_data.get("domain")
            category_obj = form.cleaned_data.get("domain_category")
            overview = (form.cleaned_data.get("overview") or "").strip()

            generate_kwargs = {
                "user": user,
                "domain": domain_obj.domain_name,
                "domain_category": category_obj.domain_name,
                "overview": overview,
            }

            generation_input = {
                "user": user.pk if user else None,
                "user_email": user.email if user else "",
                **generate_kwargs,
            }

            diagnostics = {
                "requested_by": getattr(request.user, "email", ""),
                "provider": _provider_status(),
                "input": generation_input,
            }

            try:
                service = ProjectRecommendationService()
                data, token_usage = service.generate(**generate_kwargs)
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
