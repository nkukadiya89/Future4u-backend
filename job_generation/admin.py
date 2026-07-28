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

from ai.config import is_configured
from city.models import City
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from country.models import Country
from internship_job.models import Job
from job_generation.constants.job_generation_constants import (
    JOB_OVERVIEW_MAX_LENGTH,
    JOB_TITLE_MAX_LENGTH,
)
from job_generation.exceptions import (
    JobGenerationConfigurationError,
    JobGenerationValidationError,
)
from job_generation.models import JobGenerationPanel
from job_generation.services.job_generation_service import _build_response
from job_generation.services.job_generator import JobGenerator
from state.models import State
from user_profile.models import CorporateProfile


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    from ai.config import llm_provider

    configured = is_configured()
    enabled = getattr(settings, "JOB_GENERATION_ENABLED", True)
    pname = llm_provider()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {pname} not configured"
    else:
        mode = f"{pname} job generation"
    return {
        "job_generation_enabled": enabled,
        "provider_name": pname,
        "provider_configured": configured,
        "ai_llm_enabled": configured,
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class JobGenerationRunForm(forms.Form):
    job_title = forms.CharField(
        required=False,
        max_length=JOB_TITLE_MAX_LENGTH,
        help_text="Optional. Desired job title hint for AI generation (e.g. 'Senior Data Analyst').",
    )
    job_overview = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=10,
        max_length=JOB_OVERVIEW_MAX_LENGTH,
        help_text="Required. Brief role overview for AI generation (10–1000 characters).",
    )
    corporate = forms.ModelChoiceField(
        queryset=CorporateProfile.objects.filter(deleted=False),
        required=True,
        empty_label="Select a company",
        help_text="Select the company posting this job.",
    )
    country = forms.ModelChoiceField(
        required=False,
        queryset=Country.objects.filter(deleted=False),
        empty_label="Select a country",
        help_text="Optional. Select the job location country.",
    )
    state = forms.ModelChoiceField(
        required=False,
        queryset=State.objects.filter(deleted=False),
        empty_label="Select a state",
        help_text="Optional. Select the job location state.",
    )
    city = forms.ModelChoiceField(
        required=False,
        queryset=City.objects.filter(deleted=False).select_related("country", "state"),
        empty_label="Select a city",
        help_text="Optional. Select the job location city.",
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
                    {
                        "salary_max": "salary_max must be greater than or equal to salary_min."
                    }
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
            corporate_profile = form.cleaned_data.get("corporate")
            country = form.cleaned_data.get("country")
            state = form.cleaned_data.get("state")
            city = form.cleaned_data.get("city")

            # Build the generation input with model instances for _build_response
            generation_input = {
                "job_title": form.cleaned_data.get("job_title", ""),
                "job_overview": form.cleaned_data["job_overview"],
                "corporate": corporate_profile.pk if corporate_profile else None,
                "company_name": (
                    corporate_profile.company_name if corporate_profile else ""
                ),
                "company_website": (
                    corporate_profile.website if corporate_profile else ""
                ),
                "company_about_us": (
                    corporate_profile.about_us if corporate_profile else ""
                ),
                "country": country,
                "state": state,
                "city": city,
                "job_type": form.cleaned_data.get("job_type", ""),
                "experience_level": form.cleaned_data.get("experience_level", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "salary_min": form.cleaned_data.get("salary_min"),
                "salary_max": form.cleaned_data.get("salary_max"),
                "application_deadline": form.cleaned_data.get("application_deadline"),
            }

            # Diagnostics uses only primitive values to avoid ORM conflicts
            diagnostics = {
                "requested_by": getattr(request.user, "email", ""),
                "provider": _provider_status(),
                "input": {
                    k: getattr(v, "pk", v) if hasattr(v, "_meta") else v
                    for k, v in generation_input.items()
                },
            }
            try:
                payload = JobGenerator.generate(generation_input=generation_input)
                result = _build_response(
                    payload, generation_input, company=corporate_profile
                )
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
