"""
Django admin for AI job generation (job_generation).

No database table; changelist is a live panel to test AI job posting generation.

URL: /admin/job_generation/jobgenerationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from common.mixins.admin_mixins import ReadOnlyAdminMixin
from job_generation.config import ai_llm_enabled, job_generation_enabled
from city.models import City
from internship_job.models import Job
from job_generation.constants.job_generation_constants import (
    JOB_OVERVIEW_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from job_generation.exceptions import (
    JobGenerationConfigurationError,
    JobGenerationValidationError,
)
from job_generation.models import JobGenerationPanel
from job_generation.providers.factory import get_llm_provider
from job_generation.services.job_generation_service import _build_response
from job_generation.services.job_generator import JobGenerator


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    provider = get_llm_provider()
    configured = provider.is_configured()
    enabled = job_generation_enabled()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {provider.provider_name()} not configured"
    else:
        mode = f"{provider.provider_name()} job generation"
    return {
        "job_generation_enabled": enabled,
        "provider_name": provider.provider_name(),
        "provider_configured": configured,
        "ai_llm_enabled": ai_llm_enabled(),
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class JobGenerationRunForm(forms.Form):
    job_overview = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=10,
        max_length=JOB_OVERVIEW_MAX_LENGTH,
        help_text="Required. Brief role overview for AI generation (10–1000 characters).",
    )
    organization_name = forms.CharField(
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Required. Company or organization name (user-provided).",
    )
    city = forms.IntegerField(
        required=False,
        help_text="Optional. City ID from the city master list.",
    )
    job_type = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Job.JOB_TYPE_CHOICE,
        help_text="Optional. Job type (same values as Job model).",
    )
    experience_level = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Job.EXPERIENCE_CHOICES,
        help_text="Optional. Experience level (same values as Job model).",
    )
    mode = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Job.MODE_CHOICES,
        help_text="Optional. Work mode (same values as Job model).",
    )
    salary_min = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        help_text="Optional. Minimum salary in INR (e.g. 400000).",
    )
    salary_max = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        help_text="Optional. Maximum salary in INR (e.g. 600000).",
    )

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")
        if salary_min is not None and salary_max is not None:
            if salary_min > salary_max:
                raise forms.ValidationError(
                    {"salary_max": "salary_max must be greater than or equal to salary_min."}
                )
        return cleaned_data
    application_deadline = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        help_text="Optional. Use DD/MM/YYYY (e.g. 20/07/2027) or YYYY-MM-DD.",
    )


@admin.register(JobGenerationPanel)
class JobGenerationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = JobGenerationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            city = None
            city_id = form.cleaned_data.get("city")
            if city_id:
                city = City.objects.filter(id=city_id, deleted=False).first()
            generation_input = {
                "job_overview": form.cleaned_data["job_overview"],
                "organization_name": form.cleaned_data["organization_name"],
                "city": city,
                "job_type": form.cleaned_data.get("job_type", ""),
                "experience_level": form.cleaned_data.get("experience_level", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "salary_min": form.cleaned_data.get("salary_min"),
                "salary_max": form.cleaned_data.get("salary_max"),
                "application_deadline": form.cleaned_data.get("application_deadline"),
            }
            try:
                diagnostics = {
                    "requested_by": getattr(request.user, "email", ""),
                    "provider": _provider_status(),
                    "input": generation_input,
                }
                payload = JobGenerator.generate(generation_input=generation_input)
                result = _build_response(payload, generation_input)
            except JobGenerationConfigurationError as exc:
                error = f"AI not configured: {exc}"
            except JobGenerationValidationError as exc:
                error = f"AI generation failed ({exc.error}): {exc.details}"
            except Exception as exc:
                error = f"Unexpected error: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Job Generation",
            "form": form,
            "provider": _provider_status(),
            "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/job_generation/panel.html", context)
