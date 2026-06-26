"""
Django admin for AI internship generation (internship_generation).

No database table; changelist is a live panel to test AI internship detail generation.

URL: /admin/internship_generation/internshipgenerationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from common.mixins.admin_mixins import ReadOnlyAdminMixin
from internship_generation.config import ai_llm_enabled, internship_generation_enabled
from internship_generation.constants.internship_generation_constants import (
    ABOUT_INTERNSHIP_INPUT_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from internship_generation.exceptions import (
    InternshipGenerationConfigurationError,
    InternshipGenerationValidationError,
)
from internship_generation.models import InternshipGenerationPanel
from internship_generation.providers.factory import get_llm_provider
from internship_generation.services.internship_generation_service import _build_response
from internship_generation.services.internship_generator import InternshipGenerator


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    provider = get_llm_provider()
    configured = provider.is_configured()
    enabled = internship_generation_enabled()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {provider.provider_name()} not configured"
    else:
        mode = f"{provider.provider_name()} internship generation"
    return {
        "internship_generation_enabled": enabled,
        "provider_name": provider.provider_name(),
        "provider_configured": configured,
        "ai_llm_enabled": ai_llm_enabled(),
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class InternshipGenerationRunForm(forms.Form):
    about_internship = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=10,
        max_length=ABOUT_INTERNSHIP_INPUT_MAX_LENGTH,
        help_text="Required. Brief internship overview for AI generation (10-2000 characters).",
    )
    department = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Department.",
    )
    stipend = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Monthly stipend.",
    )
    duration = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Internship duration.",
    )
    mode = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Work mode (e.g. Remote).",
    )
    application_deadline = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        help_text="Optional. Use DD/MM/YYYY (e.g. 20/07/2027) or YYYY-MM-DD.",
    )


@admin.register(InternshipGenerationPanel)
class InternshipGenerationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = InternshipGenerationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            generation_input = {
                "about_internship": form.cleaned_data["about_internship"],
                "department": form.cleaned_data.get("department", ""),
                "stipend": form.cleaned_data.get("stipend", ""),
                "duration": form.cleaned_data.get("duration", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "application_deadline": form.cleaned_data.get("application_deadline"),
            }
            try:
                diagnostics = {
                    "requested_by": getattr(request.user, "email", ""),
                    "provider": _provider_status(),
                    "input": generation_input,
                }
                payload = InternshipGenerator.generate(generation_input=generation_input)
                result = _build_response(payload, generation_input)
            except InternshipGenerationConfigurationError as exc:
                error = f"AI not configured: {exc}"
            except InternshipGenerationValidationError as exc:
                error = f"AI generation failed ({exc.error}): {exc.details}"
            except Exception as exc:
                error = f"Unexpected error: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Internship Generation",
            "form": form,
            "provider": _provider_status(),
            "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/internship_generation/panel.html", context)
