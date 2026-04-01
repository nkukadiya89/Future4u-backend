import json

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.shortcuts import render
from django.urls import path

from assessment.models import Option, Question, UserResponse
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


def _qa_relevant_questions(*, stream_id, per_dimension: int = 3) -> list[Question]:
    """
    Prefer questions mapped to domains relevant to the selected stream.
    Fallback to all active questions if no mapping exists.
    """
    base = (
        Question.objects.filter(is_active=True)
        .prefetch_related("options")
        .order_by("-signal_strength", "id")
    )
    if not stream_id:
        return _pick_questions_per_dimension(list(base), per_dimension=per_dimension)

    domain_ids = list(
        StreamDomainMapping.objects.filter(
            stream_id=stream_id,
            deleted=False,
            is_active=True,
            stream__deleted=False,
            stream__is_active=True,
            domain__deleted=False,
            domain__is_active=True,
        )
        .values_list("domain_id", flat=True)
        .distinct()
    )
    if not domain_ids:
        return _pick_questions_per_dimension(list(base), per_dimension=per_dimension)

    rows = list(
        base.filter(mapped_domains__id__in=domain_ids)
        .distinct()
    )
    picked = _pick_questions_per_dimension(rows, per_dimension=per_dimension)
    if picked:
        return picked
    return _pick_questions_per_dimension(list(base), per_dimension=per_dimension)


def _pick_questions_per_dimension(rows: list[Question], *, per_dimension: int) -> list[Question]:
    """
    Pick up to N questions per dimension, prioritizing higher signal_strength.
    """
    by_dim: dict[str, list[Question]] = {d: [] for d in DIMENSIONS}
    for q in rows:
        dim = getattr(q, "dimension", None)
        if dim in by_dim:
            by_dim[dim].append(q)
    out: list[Question] = []
    for d in DIMENSIONS:
        out.extend(by_dim[d][: max(0, int(per_dimension))])
    return out


def _upsert_user_responses(*, user_id: int, answers: dict[int, int]) -> None:
    """
    answers: {question_id: option_id}
    Upserts UserResponse rows (unique per user+question).
    """
    if not answers:
        return
    qids = list(answers.keys())
    existing = {
        r.question_id: r
        for r in UserResponse.objects.filter(user_id=user_id, question_id__in=qids)
        .only("id", "question_id", "selected_option_id", "score_value")
    }
    opt_ids = list(set(answers.values()))
    options = {o.id: o for o in Option.objects.filter(id__in=opt_ids).only("id", "question_id", "score_value")}

    to_create: list[UserResponse] = []
    to_update: list[UserResponse] = []
    for qid, oid in answers.items():
        opt = options.get(oid)
        if not opt or int(opt.question_id) != int(qid):
            raise ValueError(f"Invalid option for question {qid}")
        if qid in existing:
            r = existing[qid]
            r.selected_option_id = oid
            r.score_value = int(opt.score_value)
            to_update.append(r)
        else:
            to_create.append(
                UserResponse(
                    user_id=user_id,
                    question_id=qid,
                    selected_option_id=oid,
                    score_value=int(opt.score_value),
                )
            )
    if to_create:
        UserResponse.objects.bulk_create(to_create, ignore_conflicts=True)
    if to_update:
        UserResponse.objects.bulk_update(to_update, ["selected_option_id", "score_value"])


def _recommendation_qa_view(request):
    """
    QA admin page:
    - can optionally save assessment answers (UserResponse) for the selected user
    - runs recommendation engine for a selected user and shows diagnostics
    """
    form = RecommendationQAForm(request.GET or None)
    ctx = None
    dim_scores = None
    result = None
    diagnostics = None
    error = None
    questions: list[Question] = []
    existing_answers: dict[int, int] = {}
    saved = False

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

            effective_stream_id = ctx.stream_id if ctx else None
            questions = _qa_relevant_questions(stream_id=effective_stream_id, per_dimension=3)
            if questions:
                qids = [q.id for q in questions]
                existing_answers = {
                    r.question_id: r.selected_option_id
                    for r in UserResponse.objects.filter(user_id=user.id, question_id__in=qids)
                    .only("question_id", "selected_option_id")
                }

            if request.method == "POST" and request.POST.get("_qa_submit") == "1":
                answers: dict[int, int] = {}
                missing = 0
                for q in questions:
                    raw = request.POST.get(f"q_{q.id}")
                    if not raw:
                        missing += 1
                        continue
                    try:
                        answers[int(q.id)] = int(raw)
                    except (TypeError, ValueError):
                        missing += 1
                if missing:
                    raise ValueError(f"Please answer all questions ({missing} missing).")
                with transaction.atomic():
                    _upsert_user_responses(user_id=user.id, answers=answers)
                saved = True
                existing_answers = answers

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
        "questions": questions,
        "existing_answers": existing_answers,
        "saved": saved,
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

