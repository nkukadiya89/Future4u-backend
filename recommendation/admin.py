"""
Django admin for AI career recommendations (recommendation).

No database table; changelist is a live panel to test AI recommendations
against student, parent, and professional assessments.

URL: /admin/recommendation/airecommendationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from ai.config import groq_api_key, is_configured
from assessment.models import (
    ParentAssessment,
    ProfessionalAssessment,
    StudentAssessment,
)
from common.mixins.admin_mixins import ReadOnlyAdminMixin
from recommendation.config import ai_recommendations_enabled
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.models import AIRecommendationPanel
from recommendation.profiles.parent.service import ParentRecommendationService
from recommendation.profiles.professional.service import (
    ProfessionalRecommendationService,
)
from recommendation.profiles.student.service import StudentRecommendationService

ASSESSMENT_TYPE_CHOICES = [
    ("student", "Student"),
    ("parent", "Parent"),
    ("professional", "Professional"),
]


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    configured = is_configured()
    use_llm = ai_recommendations_enabled()
    if not use_llm:
        mode = "disabled"
    elif not configured:
        mode = "enabled, Groq key missing"
    else:
        mode = "Groq GPT OSS recommendations"
    return {
        "ai_recommendations_enabled": use_llm,
        "groq_configured": configured,
        "ai_tracing_enabled": bool(
            getattr(settings, "LANGSMITH_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


def _assessment_queryset(assessment_type):
    if assessment_type == "parent":
        return (
            ParentAssessment.objects.filter(
                deleted=False, domain_category__isnull=False
            )
            .select_related("user", "domain_category", "child")
            .order_by("-id")
        )
    if assessment_type == "professional":
        return (
            ProfessionalAssessment.objects.filter(deleted=False, domain__isnull=False)
            .select_related("user", "domain_category", "domain")
            .order_by("-id")
        )
    return (
        StudentAssessment.objects.filter(deleted=False, domain__isnull=False)
        .select_related("user", "domain", "domain_category")
        .order_by("-id")
    )


def _assessment_service(assessment_type):
    if assessment_type == "parent":
        return ParentRecommendationService()
    if assessment_type == "professional":
        return ProfessionalRecommendationService()
    return StudentRecommendationService()


class AIRecommendationRunForm(forms.Form):
    assessment_type = forms.ChoiceField(
        choices=ASSESSMENT_TYPE_CHOICES,
        initial="student",
        required=True,
    )
    assessment = forms.TypedChoiceField(
        choices=[],
        coerce=int,
        required=True,
        empty_value=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assessment_type = (
            self.data.get("assessment_type", "student") if self.is_bound else "student"
        )
        qs = _assessment_queryset(assessment_type)
        assessments = list(qs[:500])
        if self.is_bound:
            raw = self.data.get("assessment")
            if raw:
                try:
                    selected_id = int(raw)
                except (TypeError, ValueError):
                    selected_id = None
                if selected_id and not any(a.id == selected_id for a in assessments):
                    extra = qs.filter(pk=selected_id).first()
                    if extra:
                        assessments.insert(0, extra)
        self.fields["assessment"].choices = [(a.id, str(a)) for a in assessments]

    def clean_assessment(self):
        assessment_id = self.cleaned_data["assessment"]
        assessment_type = self.cleaned_data.get("assessment_type", "student")
        qs = _assessment_queryset(assessment_type)
        if not qs.filter(pk=assessment_id).exists():
            raise forms.ValidationError("Select a valid assessment.")
        return assessment_id


@admin.register(AIRecommendationPanel)
class AIRecommendationPanelAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        form = AIRecommendationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            assessment_id = form.cleaned_data["assessment"]
            assessment_type = form.cleaned_data["assessment_type"]
            assessment = _assessment_queryset(assessment_type).get(pk=assessment_id)
            try:
                diagnostics = {
                    "assessment_id": assessment.id,
                    "user_id": assessment.user_id,
                    "user_email": getattr(assessment.user, "email", ""),
                    "type": assessment_type,
                    "domain": getattr(
                        assessment,
                        (
                            "domain_category_id"
                            if assessment_type == "parent"
                            else "domain_id"
                        ),
                        None,
                    ),
                    "is_completed": assessment.is_completed,
                    "current_screen": assessment.current_screen,
                    "provider": _provider_status(),
                }
                result = _assessment_service(assessment_type).generate(
                    assessment_id=assessment.id,
                    user=assessment.user,
                )
            except AssessmentNotFoundError:
                error = "Assessment not found."
            except AssessmentAccessDeniedError:
                error = "Assessment access denied."
            except AssessmentNotReadyError as exc:
                error = str(exc)
            except AIConfigurationError as exc:
                error = f"AI not configured: {exc}"
            except AIGenerationError as exc:
                error = f"AI generation failed: {exc}"
            except Exception as exc:
                error = f"Unexpected error: {exc}"

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Recommendations",
            "form": form,
            "provider": _provider_status(),
            "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
            "result_pretty": _pretty_json(result) if result else None,
            "error": error,
            "opts": self.model._meta,
            "cl": type("cl", (), {"opts": self.model._meta})(),
        }
        return render(request, "admin/ai/panel.html", context)
