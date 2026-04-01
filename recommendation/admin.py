import json

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import render
from django.urls import path

from assessment.models import Question, UserResponse
from education_level.models import EducationLevel
from services.recommendation_engine_service import (
    DIMENSIONS,
    TIER_10TH,
    _assessment_dimension_scores,
    _fetch_context,
    _UserContext,
    generate_recommendation,
)
from stream.models import Stream
from stream_domain_mapping.models import StreamDomainMapping


class RecommendationQAForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("-id"),
        required=True,
        help_text="Select a student/user to run the recommendation engine (read-only).",
    )
    education_level = forms.ModelChoiceField(
        queryset=EducationLevel.objects.filter(is_active=True, deleted=False).order_by("sequence_order"),
        required=False,
        help_text="Optional override (not saved). If set, engine will run as if user has this education level.",
    )
    stream = forms.ModelChoiceField(
        queryset=Stream.objects.filter(is_active=True, deleted=False).order_by("stream_name"),
        required=False,
        help_text="Optional override (not saved). Required for 12th+ tiers.",
    )


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _recommendation_qa_view(request):
    """
    Safe QA admin page:
    - does not write any DB changes
    - runs recommendation engine for a selected user and shows diagnostics
    """
    form = RecommendationQAForm(request.GET or None)
    ctx = None
    dim_scores = None
    result = None
    diagnostics = None
    error = None

    if form.is_valid():
        user = form.cleaned_data["user"]
        try:
            ctx_profile = _fetch_context(user_id=user.id)
            ctx = ctx_profile

            # Optional overrides (read-only)
            edu = form.cleaned_data.get("education_level")
            stream = form.cleaned_data.get("stream")
            override_active = bool(edu or stream)
            if override_active:
                seq = int(getattr(edu, "sequence_order", 0) or 0) if edu else (ctx_profile.education_sequence if ctx_profile else 0)
                stream_id = stream.pk if stream else (ctx_profile.stream_id if ctx_profile else None)
                stream_code = getattr(stream, "stream_code", "") or "" if stream else (ctx_profile.stream_code if ctx_profile else "")

                # Mirror profile rule: from 12th onwards stream is required.
                if seq > TIER_10TH and not stream_id:
                    ctx = None
                else:
                    ctx = _UserContext(
                        user_id=user.id,
                        stream_id=stream_id,
                        stream_code=stream_code,
                        education_sequence=seq,
                    )
            dim_scores = _assessment_dimension_scores(user_id=user.id)
            result = generate_recommendation(user.id, ctx_override=ctx)

            # Diagnostics: assessment coverage and mapping counts
            totals = {
                r["dimension"]: int(r["total"] or 0)
                for r in Question.objects.filter(is_active=True)
                .values("dimension")
                .annotate(total=Count("id"))
            }
            answered = {
                r["question__dimension"]: int(r["answered"] or 0)
                for r in UserResponse.objects.filter(user_id=user.id, question__is_active=True)
                .values("question__dimension")
                .annotate(answered=Count("id"))
            }
            per_dim = []
            for d in DIMENSIONS:
                per_dim.append(
                    {
                        "dimension": d,
                        "answered": answered.get(d, 0),
                        "total": totals.get(d, 0),
                        "score_0_100": round(float(dim_scores.get(d, 0.0) or 0.0), 2) if dim_scores else 0.0,
                    }
                )

            mapping_count = None
            if ctx and ctx.stream_id:
                mapping_count = (
                    StreamDomainMapping.objects.filter(
                        stream_id=ctx.stream_id,
                        deleted=False,
                        is_active=True,
                        stream__deleted=False,
                        stream__is_active=True,
                        domain__deleted=False,
                        domain__is_active=True,
                    )
                    .values("domain_id")
                    .distinct()
                    .count()
                )

            diagnostics = {
                "profile_context": None if ctx_profile is None else {
                    "education_sequence": ctx_profile.education_sequence,
                    "stream_id": str(ctx_profile.stream_id) if ctx_profile.stream_id else None,
                    "stream_code": ctx_profile.stream_code,
                },
                "override_context": None if (ctx is None or ctx == ctx_profile) else {
                    "education_sequence": ctx.education_sequence,
                    "stream_id": str(ctx.stream_id) if ctx.stream_id else None,
                    "stream_code": ctx.stream_code,
                },
                "assessment_by_dimension": per_dim,
                "active_domains_mapped_to_stream_count": mapping_count,
            }
        except Exception as exc:
            error = str(exc)

    context = {
        **admin.site.each_context(request),
        "title": "Recommendation QA (read-only)",
        "form": form,
        "ctx": ctx,
        "dim_scores_pretty": _pretty_json(dim_scores) if dim_scores is not None else None,
        "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics is not None else None,
        "result_pretty": _pretty_json(result) if result is not None else None,
        "error": error,
    }
    return render(request, "admin/recommendation/qa.html", context)


# Ensure the admin index (home page) shows a Tools link.
# This is more reliable than trying to override admin/index.html via app templates,
# because Django resolves app templates in INSTALLED_APPS order and
# django.contrib.admin appears first.
admin.site.index_template = "admin/recommendation_index.html"


# Inject a custom admin URL without adding new models.
_old_get_urls = admin.site.get_urls


def _get_urls():
    urls = _old_get_urls()
    custom = [
        path(
            "recommendation/qa/",
            admin.site.admin_view(_recommendation_qa_view),
            name="recommendation-qa",
        )
    ]
    return custom + urls


admin.site.get_urls = _get_urls

