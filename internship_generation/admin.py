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

from ai.config import is_configured
from city.models import City
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from country.models import Country
from internship_generation.constants.internship_generation_constants import (
    INTERNSHIP_OVERVIEW_INPUT_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from internship_generation.exceptions import (
    InternshipGenerationConfigurationError,
    InternshipGenerationValidationError,
)
from internship_generation.models import InternshipGenerationPanel
from internship_generation.services.internship_generation_service import _build_response
from internship_generation.services.internship_generator import InternshipGenerator
from internship_job.models import Internship
from state.models import State
from user.models import User


class InternshipProviderUserChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that displays the institute/corporate name instead of the user email."""

    def label_from_instance(self, obj):
        name = None
        if hasattr(obj, "institute_profile"):
            name = obj.institute_profile.institute_name
        elif hasattr(obj, "corporate_profile"):
            name = obj.corporate_profile.company_name
        if name:
            return f"{name} ({obj.user_type})"
        return obj.full_name or obj.email


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    from ai.config import llm_provider

    configured = is_configured()
    enabled = getattr(settings, "INTERNSHIP_GENERATION_ENABLED", True)
    pname = llm_provider()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {pname} not configured"
    else:
        mode = f"{pname} internship generation"
    return {
        "internship_generation_enabled": enabled,
        "provider_name": pname,
        "provider_configured": configured,
        "ai_llm_enabled": configured,
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class InternshipGenerationRunForm(forms.Form):
    internship_title = forms.CharField(
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Required. Internship title (e.g. 'Marketing Intern').",
    )
    internship_overview = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=10,
        max_length=INTERNSHIP_OVERVIEW_INPUT_MAX_LENGTH,
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
    mode = forms.ChoiceField(
        choices=(("", "---------"),) + Internship.MODE_CHOICE,
        required=False,
        help_text="Optional. Work mode.",
    )
    country = forms.ModelChoiceField(
        required=False,
        queryset=Country.objects.filter(deleted=False),
        empty_label="Select a country",
        help_text="Optional. Select the internship location country.",
    )
    state = forms.ModelChoiceField(
        required=False,
        queryset=State.objects.filter(deleted=False),
        empty_label="Select a state",
        help_text="Optional. Select the internship location state.",
    )
    city = forms.ModelChoiceField(
        required=False,
        queryset=City.objects.filter(deleted=False).select_related("country", "state"),
        empty_label="Select a city",
        help_text="Optional. Select the internship location city.",
    )
    application_deadline = forms.DateField(
        required=False,
        input_formats=["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"],
        help_text="Optional. Use DD/MM/YYYY (e.g. 20/07/2027) or YYYY-MM-DD.",
    )
    certificate_provided = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Optional. Whether a completion certificate is provided (default: yes).",
    )
    # Dropdown 1 — type of organisation
    provider_type = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Internship.PROVIDER_TYPE_CHOICES,
        help_text="Optional. Select whether the internship is posted by an Institute or a Corporate.",
    )
    # Dropdown 2 — specific user of the selected provider_type
    internship_provider = InternshipProviderUserChoiceField(
        required=False,
        queryset=User.objects.filter(
            user_type__in=["institute", "corporate"],
            deleted=False,
        )
        .select_related("institute_profile", "corporate_profile")
        .order_by("full_name"),
        label="Internship Provider",
        empty_label="Select an internship provider",
        help_text="Optional. Select the institute or corporate posting this internship.",
    )

    def clean(self):
        cleaned = super().clean()
        provider_type = cleaned.get("provider_type") or ""
        internship_provider = cleaned.get("internship_provider")

        if internship_provider and provider_type:
            if internship_provider.user_type != provider_type:
                self.add_error(
                    "internship_provider",
                    f"Selected user does not belong to the '{provider_type}' type.",
                )
        return cleaned


@admin.register(InternshipGenerationPanel)
class InternshipGenerationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = InternshipGenerationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            country = form.cleaned_data.get("country")
            state = form.cleaned_data.get("state")
            city = form.cleaned_data.get("city")
            generation_input = {
                "internship_title": form.cleaned_data.get("internship_title", ""),
                "internship_overview": form.cleaned_data.get("internship_overview", ""),
                "department": form.cleaned_data.get("department", ""),
                "stipend": form.cleaned_data.get("stipend", ""),
                "duration": form.cleaned_data.get("duration", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "country": country,
                "state": state,
                "city": city,
                "application_deadline": form.cleaned_data.get("application_deadline"),
                "certificate_provided": form.cleaned_data.get(
                    "certificate_provided", True
                ),
                "provider_type": form.cleaned_data.get("provider_type", ""),
                "internship_provider": form.cleaned_data.get("internship_provider"),
            }
            try:
                diagnostics = {
                    "requested_by": getattr(request.user, "email", ""),
                    "provider": _provider_status(),
                    "input": {
                        k: getattr(v, "pk", v) if hasattr(v, "_meta") else v
                        for k, v in generation_input.items()
                    },
                }
                payload = InternshipGenerator.generate(
                    generation_input=generation_input
                )
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
