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

from common.mixins.admin_mixins import ReadOnlyAdminMixin
from course.models import Courses
from course_generation.config import ai_llm_enabled, course_generation_enabled
from course_generation.constants.course_generation_constants import (
    COURSE_OVERVIEW_MAX_LENGTH,
    OPTIONAL_FIELD_MAX_LENGTH,
)
from course_generation.exceptions import (
    CourseGenerationConfigurationError,
    CourseGenerationValidationError,
)
from course_generation.models import CourseGenerationPanel
from course_generation.providers.factory import get_llm_provider
from course_generation.services.course_generation_service import _build_response
from course_generation.services.course_generator import CourseGenerator


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


@admin.register(CourseGenerationPanel)
class CourseGenerationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = CourseGenerationRunForm(request.POST or None)
        result = None
        error = None

        if request.method == "POST" and form.is_valid():
            generation_input = {
                "course_overview": form.cleaned_data["course_overview"],
                "course_price": form.cleaned_data.get("course_price", ""),
                "course_type": form.cleaned_data.get("course_type", ""),
                "mode": form.cleaned_data.get("mode", ""),
                "duration": form.cleaned_data.get("duration", ""),
            }
            try:
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
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/course_generation/panel.html", context)
