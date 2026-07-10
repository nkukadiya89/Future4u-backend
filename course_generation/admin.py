"""
Django admin for AI course generation (course_generation).

No database table; changelist is a live panel to test AI course detail generation.

URL: /admin/course_generation/coursegenerationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from city.models import City
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from country.models import Country
from course.models import Courses
from course_generation.config import ai_llm_enabled, course_generation_enabled
from course_generation.constants.course_generation_constants import (
    COURSE_OVERVIEW_MAX_LENGTH,
    COURSE_TITLE_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from state.models import State
from user.models import User
from course_generation.exceptions import (
    CourseGenerationConfigurationError,
    CourseGenerationValidationError,
)
from course_generation.models import CourseGenerationPanel
from course_generation.providers.factory import get_llm_provider
from course_generation.services.course_generation_service import _build_response
from course_generation.services.course_generator import CourseGenerator


class InstituteUserChoiceField(forms.ModelChoiceField):
    """ModelChoiceField that displays the institute/school-college name instead of the user email."""

    def label_from_instance(self, obj):
        # Try institute profile first, then school-college profile
        name = None
        if hasattr(obj, "institute_profile"):
            name = obj.institute_profile.institute_name
        elif hasattr(obj, "school_college_profile"):
            name = obj.school_college_profile.institute_name
        if name:
            return f"{name} ({obj.user_type})"
        return obj.full_name or obj.email


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    provider = get_llm_provider()
    configured = provider.is_configured()
    enabled = course_generation_enabled()
    if not enabled:
        mode = "disabled"
    elif not configured:
        mode = f"enabled, {provider.provider_name()} not configured"
    else:
        mode = f"{provider.provider_name()} course generation"
    return {
        "course_generation_enabled": enabled,
        "provider_name": provider.provider_name(),
        "provider_configured": configured,
        "ai_llm_enabled": ai_llm_enabled(),
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


class CourseGenerationRunForm(forms.Form):
    course_title = forms.CharField(
        required=False,
        max_length=COURSE_TITLE_MAX_LENGTH,
        help_text="Optional. Course title hint (e.g. 'Full Stack Web Development'). AI will refine it.",
    )
    course_overview = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        min_length=10,
        max_length=COURSE_OVERVIEW_MAX_LENGTH,
        help_text="Required. Brief course overview for AI generation (10-2000 characters).",
    )
    course_price = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Course price.",
    )
    course_type = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Courses.COURSE_TYPE_CHOICES,
        help_text="Optional. Course type (same values as Courses model).",
    )
    mode = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Courses.MODE_CHOICE,
        help_text="Optional. Delivery mode (same values as Courses model).",
    )
    duration = forms.CharField(
        required=False,
        max_length=OPTIONAL_FIELD_MAX_LENGTH,
        help_text="Optional. Course duration.",
    )
    country = forms.ModelChoiceField(
        required=False,
        queryset=Country.objects.filter(deleted=False),
        empty_label="Select a country",
        help_text="Optional. Select the course location country.",
    )
    state = forms.ModelChoiceField(
        required=False,
        queryset=State.objects.filter(deleted=False),
        empty_label="Select a state",
        help_text="Optional. Select the course location state.",
    )
    city = forms.ModelChoiceField(
        required=False,
        queryset=City.objects.filter(deleted=False).select_related("country", "state"),
        empty_label="Select a city",
        help_text="Optional. Select the course location city.",
    )
    # Dropdown 1 — type of organisation
    provider_type = forms.ChoiceField(
        required=False,
        choices=(("", "---------"),) + Courses.PROVIDER_TYPE_CHOICES,
        help_text="Optional. Select whether the course is posted by a School/College or an Institute.",
    )
    # Dropdown 2 — specific user of the selected provider_type
    course_provider = InstituteUserChoiceField(
        required=False,
        queryset=User.objects.filter(
            user_type__in=["school_college", "institute"],
            deleted=False,
        ).select_related("institute_profile", "school_college_profile").order_by("full_name"),
        label="Course Provider",
        empty_label="Select a course provider",
        help_text="Optional. Select the institute or school/college posting this course.",
    )

    def clean(self):
        cleaned = super().clean()
        provider_type = cleaned.get("provider_type") or ""
        course_provider = cleaned.get("course_provider")

        if course_provider and provider_type:
            if course_provider.user_type != provider_type:
                self.add_error(
                    "course_provider",
                    f"Selected user does not belong to the '{provider_type}' type.",
                )
        return cleaned


@admin.register(CourseGenerationPanel)
class CourseGenerationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = CourseGenerationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            country = form.cleaned_data.get("country")
            state = form.cleaned_data.get("state")
            city = form.cleaned_data.get("city")

            generation_input = {
                "course_title": form.cleaned_data.get("course_title", ""),
                "course_overview": form.cleaned_data["course_overview"],
                "course_price": form.cleaned_data.get("course_price", ""),
                "course_type": form.cleaned_data.get("course_type", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "duration": form.cleaned_data.get("duration", ""),
                "country": country,
                "state": state,
                "city": city,
                "provider_type": form.cleaned_data.get("provider_type", ""),
                "course_provider": form.cleaned_data.get("course_provider"),
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
                payload = CourseGenerator.generate(generation_input=generation_input)
                result = _build_response(payload, generation_input)
            except CourseGenerationConfigurationError as exc:
                error = f"AI not configured: {exc}"
            except CourseGenerationValidationError as exc:
                error = f"AI generation failed ({exc.error}): {exc.details}"
            except Exception as exc:
                error = f"Unexpected error: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Course Generation",
            "form": form,
            "provider": _provider_status(),
            "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/course_generation/panel.html", context)
