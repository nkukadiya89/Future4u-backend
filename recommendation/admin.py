import json

from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from django.shortcuts import render
from django.urls import path

from assessment.models import Option, Question, UserResponse
from services.recommendation_engine_service import RecommendationEngineService
from education_level.models import EducationLevel
from stream.models import Stream


DIMENSIONS = ["interest", "aptitude", "personality", "work_style"]


class RecommendationQAForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.all().order_by("-id"),
        required=True,
        help_text="Select a student/user to run the recommendation engine.",
    )
    education_level = forms.ModelChoiceField(
        queryset=EducationLevel.objects.filter(is_active=True, deleted=False).order_by(
            "sequence_order"
        ),
        required=False,
        help_text="Optional override (not saved).",
    )
    stream = forms.ModelChoiceField(
        queryset=Stream.objects.filter(is_active=True, deleted=False).order_by(
            "stream_name"
        ),
        required=False,
        help_text="Optional override (not saved).",
    )


def _pretty_json(value) -> str:
    try:
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _pick_questions_per_dimension(rows: list, *, per_dimension: int = 5) -> list:
    by_dim: dict[str, list] = {d: [] for d in DIMENSIONS}
    for q in rows:
        dim = getattr(q, "dimension", None)
        if dim in by_dim:
            by_dim[dim].append(q)
    out = []
    for d in DIMENSIONS:
        out.extend(by_dim[d][:per_dimension])
    return out


def _upsert_user_responses(*, user_id: int, answers: dict) -> None:
    if not answers:
        return
    qids = list(answers.keys())
    existing = {
        r.question_id: r
        for r in UserResponse.objects.filter(
            user_id=user_id, question_id__in=qids
        ).only("id", "question_id", "selected_option_id", "score_value")
    }
    opt_ids = list(set(answers.values()))
    options = {
        o.id: o
        for o in Option.objects.filter(id__in=opt_ids).only(
            "id", "question_id", "score_value"
        )
    }

    to_create, to_update = [], []
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
        UserResponse.objects.bulk_update(
            to_update, ["selected_option_id", "score_value"]
        )


def _recommendation_qa_view(request):
    form = RecommendationQAForm(request.GET or None)
    result = None
    diagnostics = None
    questions = []
    existing_answers = {}
    saved = False
    error = None

    if form.is_valid():
        user = form.cleaned_data["user"]
        edu = form.cleaned_data.get("education_level")
        stream = form.cleaned_data.get("stream")
        try:
            # Load questions for the QA form
            questions = _pick_questions_per_dimension(
                list(
                    Question.objects.filter(is_active=True)
                    .prefetch_related("options")
                    .order_by("-signal_strength", "id")
                ),
                per_dimension=5,
            )
            if questions:
                qids = [q.id for q in questions]
                existing_answers = {
                    r.question_id: r.selected_option_id
                    for r in UserResponse.objects.filter(
                        user_id=user.id, question_id__in=qids
                    ).only("question_id", "selected_option_id")
                }

            if request.method == "POST" and request.POST.get("_qa_submit") == "1":
                answers = {}
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
                    raise ValueError(
                        f"Please answer all questions ({missing} missing)."
                    )
                with transaction.atomic():
                    _upsert_user_responses(user_id=user.id, answers=answers)
                saved = True
                existing_answers = answers

            edu_code = (getattr(edu, "level_code", "") or "").lower() if edu else None
            stream_code = (
                (getattr(stream, "stream_code", "") or "").lower() if stream else None
            )

            result = RecommendationEngineService().recommend(
                user_id=user.id,
                education_level_code=edu_code,
                stream_code=stream_code,
            )

            # Build diagnostics
            totals = {
                r["dimension"]: int(r["total"] or 0)
                for r in Question.objects.filter(is_active=True)
                .values("dimension")
                .annotate(total=Count("id"))
            }
            answered = {
                r["question__dimension"]: int(r["answered"] or 0)
                for r in UserResponse.objects.filter(
                    user_id=user.id, question__is_active=True
                )
                .values("question__dimension")
                .annotate(answered=Count("id"))
            }
            diagnostics = {
                "assessment_by_dimension": [
                    {
                        "dimension": d,
                        "answered": answered.get(d, 0),
                        "total": totals.get(d, 0),
                    }
                    for d in DIMENSIONS
                ],
                "override_context": {
                    "education_level_code": edu_code,
                    "stream_code": stream_code,
                },
                "confidence": result.get("confidence", 0),
                "recommendation_type": result.get("recommendation_type"),
                "education_level": result.get("education_level"),
            }

        except Exception as exc:
            error = str(exc)

    context = {
        **admin.site.each_context(request),
        "title": "Recommendation QA",
        "form": form,
        "questions": questions,
        "existing_answers": existing_answers,
        "saved": saved,
        "diagnostics_pretty": _pretty_json(diagnostics) if diagnostics else None,
        "result_pretty": _pretty_json(result) if result else None,
        "error": error,
    }
    return render(request, "admin/recommendation/qa.html", context)


admin.site.index_template = "admin/recommendation_index.html"

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
