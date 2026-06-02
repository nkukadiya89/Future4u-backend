"""
Django admin for AI career recommendations (recommendation).

No database table; changelist is a live panel to test AI recommendations
against student assessments.

URL: /admin/recommendation/airecommendationpanel/
"""

from __future__ import annotations

import json

from django import forms
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render

from assessment.models import StudentAssessment
from recommendation.clients.groq_client import get_groq_api_key_optional
from recommendation.config import ai_recommendations_enabled
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from recommendation.models import AIRecommendationPanel
from recommendation.services.ai_recommendation_service import AIRecommendationService


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _provider_status() -> dict:
    groq_ok = bool(get_groq_api_key_optional())
    use_llm = ai_recommendations_enabled()
    if not use_llm:
        mode = "disabled"
    elif not groq_ok:
        mode = "enabled, Groq key missing"
    else:
        mode = "Groq GPT OSS recommendations"
    return {
        "ai_recommendations_enabled": use_llm,
        "groq_configured": groq_ok,
        "ai_tracing_enabled": bool(
            getattr(settings, "AI_TRACING_ENABLED", False)
        ),
        "mode": mode,
    }


def _assessment_choices_queryset():
    return (
        StudentAssessment.objects.filter(deleted=False, domain__isnull=False)
        .select_related("user", "domain", "domain_category")
        .order_by("-id")
    )


class AIRecommendationRunForm(forms.Form):
    assessment = forms.TypedChoiceField(
        choices=[],
        coerce=int,
        required=True,
        empty_value=None,
        help_text="Student assessment used for AI recommendations (must have a domain).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assessments = list(_assessment_choices_queryset()[:500])
        if self.is_bound:
            raw = self.data.get("assessment")
            if raw:
                try:
                    selected_id = int(raw)
                except (TypeError, ValueError):
                    selected_id = None
                if selected_id and not any(a.id == selected_id for a in assessments):
                    extra = (
                        _assessment_choices_queryset()
                        .filter(pk=selected_id)
                        .first()
                    )
                    if extra:
                        assessments.insert(0, extra)
        self.fields["assessment"].choices = [
            (a.id, str(a)) for a in assessments
        ]

    def clean_assessment(self):
        assessment_id = self.cleaned_data["assessment"]
        try:
            return _assessment_choices_queryset().get(pk=assessment_id)
        except StudentAssessment.DoesNotExist as exc:
            raise forms.ValidationError(
                "Select a valid assessment with a domain assigned."
            ) from exc


@admin.register(AIRecommendationPanel)
class AIRecommendationPanelAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        form = AIRecommendationRunForm(request.POST or None)
        result = None
        diagnostics = None
        error = None

        if request.method == "POST" and form.is_valid():
            assessment = form.cleaned_data["assessment"]
            try:
                diagnostics = {
                    "assessment_id": assessment.id,
                    "user_id": assessment.user_id,
                    "user_email": getattr(assessment.user, "email", ""),
                    "domain": getattr(assessment.domain, "domain_code", None),
                    "is_completed": assessment.is_completed,
                    "current_screen": assessment.current_screen,
                    "provider": _provider_status(),
                }
                result = AIRecommendationService().generate(
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
