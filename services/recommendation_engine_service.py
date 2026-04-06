from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Count, F, FloatField, Sum
from django.db.models.expressions import ExpressionWrapper
from django.db.models import Avg, Q

from assessment.models import UserResponse
from assessment.services.counsellor_message_service import build_counsellor_message
from assessment.services.domain_config import DOMAIN_CONFIG
from assessment.services.universal_scoring_service import evaluate_domain
from career.models import Career
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from education_level.models import EducationLevel
from stream.models import Stream
from stream_domain_mapping.models import StreamDomainMapping
from user_profile.models import UserProfile
from user_skill.models import UserSkill


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

TENTH_GRADE_STREAM_CODES = {
    "science",
    "commerce",
    "arts",
    "vocational",
    "sports",
    "fine_arts",
    "agriculture",
}

LEVEL_10TH = "secondary"
LEVEL_12TH = "higher_secondary"
LEVEL_ITI = "iti"
LEVEL_DIPLOMA = "diploma"
LEVEL_GRAD = "graduation"
LEVEL_PG = "post_graduation"
LEVEL_PHD = "doctorate"
LEVEL_PROFESSIONAL = "professional"

STREAM_RECOMMENDATION_LEVELS = {LEVEL_10TH}
DOMAIN_RECOMMENDATION_LEVELS = {LEVEL_12TH}
ENTRY_CAREER_LEVELS = {LEVEL_ITI, LEVEL_DIPLOMA}
FULL_CAREER_LEVELS = {LEVEL_GRAD, LEVEL_PG, LEVEL_PHD, LEVEL_PROFESSIONAL}


@dataclass(frozen=True)
class _UserContext:
    user_id: int
    stream_id: Any
    education_sequence: int
    education_level_code: str | None


def _empty(message: str, *, education_level_code: str | None = None) -> dict[str, Any]:
    return {
        "message": message,
        "suggestion": [],
        "top_domains": [],
        "top_careers": [],
        "skill_gaps": [],
        "confidence": 0,
        "recommendation_type": "career",
        "education_level": education_level_code,
    }


def _score_1_5_to_0_100(value: float) -> float:
    # 1 -> 0, 3 -> 50, 5 -> 100
    return max(0.0, min(100.0, ((value - 1.0) / 4.0) * 100.0))


def _assessment_dimension_scores_0_100(*, user_id: int) -> dict[str, float]:
    rows = (
        UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .values("question__dimension")
        .annotate(avg=Avg("score_value"))
    )
    by_dim: dict[str, float] = {d: 50.0 for d in DIMENSIONS}
    for r in rows:
        dim = r.get("question__dimension")
        if dim in DIMENSIONS and r.get("avg") is not None:
            by_dim[dim] = _score_1_5_to_0_100(float(r["avg"]))
    return by_dim


def _base_domain_score(scores: dict[str, float]) -> float:
    # Per spec: interest 0.3, aptitude 0.35, personality 0.2, work_style 0.15
    return (
        float(scores.get("interest", 50.0)) * 0.3
        + float(scores.get("aptitude", 50.0)) * 0.35
        + float(scores.get("personality", 50.0)) * 0.2
        + float(scores.get("work_style", 50.0)) * 0.15
    )


def _top_factor(scores: dict[str, float]) -> tuple[str, float]:
    # Deterministic tie-break: DIMENSIONS order.
    best_dim = DIMENSIONS[0]
    best_val = float(scores.get(best_dim, 50.0))
    for d in DIMENSIONS[1:]:
        v = float(scores.get(d, 50.0))
        if v > best_val:
            best_dim, best_val = d, v
    return best_dim, best_val


def _estimate_skill_proficiency_40_70(*, skill_name: str, dim_scores: dict[str, float]) -> int:
    """
    Heuristic skill proficiency estimator when UserSkill is missing.
    Keeps output within 40–70 range as per UX spec.
    """
    name = (skill_name or "").strip().lower()
    aptitude = float(dim_scores.get("aptitude", 50.0))
    interest = float(dim_scores.get("interest", 50.0))
    personality = float(dim_scores.get("personality", 50.0))
    work_style = float(dim_scores.get("work_style", 50.0))

    technical_keywords = (
        "python",
        "java",
        "javascript",
        "typescript",
        "c++",
        "c#",
        "sql",
        "database",
        "coding",
        "program",
        "programming",
        "development",
        "api",
        "backend",
        "frontend",
        "cloud",
        "devops",
        "linux",
        "network",
        "data",
        "excel",
        "ai",
        "ml",
        "machine learning",
    )
    domain_keywords = (
        "marketing",
        "sales",
        "finance",
        "account",
        "accounting",
        "design",
        "ui",
        "ux",
        "health",
        "medical",
        "nursing",
        "sports",
        "education",
        "teaching",
        "law",
        "hr",
        "human resources",
        "communication",
        "writing",
        "content",
        "business",
        "management",
    )

    if any(k in name for k in technical_keywords):
        basis = aptitude
    elif any(k in name for k in domain_keywords):
        basis = interest
    else:
        basis = (aptitude * 0.45) + (interest * 0.45) + (personality * 0.05) + (work_style * 0.05)

    return int(round(max(40.0, min(70.0, 40.0 + (float(basis) / 100.0) * 30.0))))


def _domain_reason(*, top_dim: str, top_dim_score: float, mapping_weight: int, domain_future_relevance: int | None) -> str:
    dim_label = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality fit",
        "work_style": "work style fit",
    }.get(top_dim, top_dim)

    parts: list[str] = []
    if top_dim_score >= 70:
        parts.append(f"High {dim_label}")
    elif top_dim_score >= 55:
        parts.append(f"Solid {dim_label}")
    else:
        parts.append(f"Balanced {dim_label}")

    if mapping_weight >= 80:
        parts.append("strong stream alignment")
    elif mapping_weight >= 60:
        parts.append("good stream alignment")
    else:
        parts.append("moderate stream alignment")

    if domain_future_relevance is not None:
        if domain_future_relevance >= 80:
            parts.append("high future relevance")
        elif domain_future_relevance <= 40:
            parts.append("niche future relevance")

    return " and ".join(parts).capitalize()


def _career_reason(*, domain_name: str, mapping_weight: int, top_dim: str) -> str:
    dim_label = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality",
        "work_style": "work style",
    }.get(top_dim, top_dim)
    if mapping_weight >= 80:
        alignment = "strong"
    elif mapping_weight >= 60:
        alignment = "good"
    else:
        alignment = "moderate"
    return f"From {domain_name}: {alignment} fit and driven by your {dim_label}"


def _calc_confidence(*, top_domain_score: float, domain_count: int, career_count: int, has_assessment: bool) -> int:
    base = 40.0 if has_assessment else 15.0
    base += min(35.0, float(top_domain_score) * 0.35)
    base += min(10.0, domain_count * 1.0)
    base += min(10.0, career_count * 0.5)
    return int(round(max(0.0, min(88.0, base))))


def _resolve_user_context(
    *,
    user_id: int,
    education_level_code: str | None = None,
    stream_code: str | None = None,
) -> _UserContext | None:
    profile = (
        UserProfile.objects.select_related("stream", "education_level")
        .filter(user_id=user_id)
        .first()
    )
    if not profile:
        return None

    if education_level_code:
        edu = (
            EducationLevel.objects.filter(
                level_code__iexact=education_level_code,
                is_active=True,
                deleted=False,
            )
            .only("id", "sequence_order", "level_code")
            .first()
        )
    else:
        edu = getattr(profile, "education_level", None)

    if stream_code:
        stream = (
            Stream.objects.filter(
                stream_code__iexact=stream_code,
                is_active=True,
                deleted=False,
            )
            .only("id", "stream_code")
            .first()
        )
    else:
        stream = getattr(profile, "stream", None)

    if not stream or not edu:
        return None

    if getattr(stream, "deleted", False) or not getattr(stream, "is_active", True):
        return None
    if getattr(edu, "deleted", False) or not getattr(edu, "is_active", True):
        return None

    seq = int(getattr(edu, "sequence_order", 0) or 0)
    level_code = (getattr(edu, "level_code", "") or "").lower() or None
    return _UserContext(user_id=user_id, stream_id=stream.pk, education_sequence=seq, education_level_code=level_code)


def generate_recommendation(
    *,
    user_id: int,
    education_level_code: str | None = None,
    stream_code: str | None = None,
) -> dict[str, Any]:
    User = get_user_model()
    if not User.objects.filter(pk=user_id).exists():
        return _empty("User not found.")

    ctx = _resolve_user_context(user_id=user_id, education_level_code=education_level_code, stream_code=stream_code)
    if ctx is None:
        return _empty("User profile missing required education_level or active stream.")

    dim_scores = _assessment_dimension_scores_0_100(user_id=user_id)
    base = _base_domain_score(dim_scores)
    top_dim, top_dim_score = _top_factor(dim_scores)

    stream_domain_rows = list(
        StreamDomainMapping.objects.filter(
            stream_id=ctx.stream_id,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
        )
        .select_related("domain")
        .only(
            "id",
            "weight_score",
            "domain__id",
            "domain__domain_name",
            "domain__future_relevance_score",
        )
    )
    if not stream_domain_rows:
        return _empty("No active stream→domain mappings found for this user.", education_level_code=ctx.education_level_code)

    domain_items: list[dict[str, Any]] = []
    domain_score_by_id: dict[Any, float] = {}
    for m in stream_domain_rows:
        d = m.domain
        mapping_weight = int(getattr(m, "weight_score", 0) or 0)
        final = (base * 0.6) + (mapping_weight * 0.4)
        domain_score_by_id[d.pk] = float(final)
        domain_items.append(
            {
                "id": str(d.pk),
                "name": getattr(d, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": _domain_reason(
                    top_dim=top_dim,
                    top_dim_score=top_dim_score,
                    mapping_weight=mapping_weight,
                    domain_future_relevance=getattr(d, "future_relevance_score", None),
                ),
            }
        )

    domain_items.sort(key=lambda x: (-float(x["score"]), x["name"], x["id"]))
    top_domains = domain_items[:10]
    top_domain_pk_set = {int(x["id"]) for x in top_domains if str(x.get("id") or "").isdigit()}

    career_rows = list(
        DomainCareerMapping.objects.filter(
            domain_id__in=top_domain_pk_set,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
            career__deleted=False,
            career__is_active=True,
            career__min_education_level__deleted=False,
            career__min_education_level__is_active=True,
        )
        .select_related(
            "domain",
            "career",
            "career__min_education_level",
            "career__max_education_level",
        )
        .filter(career__min_education_level__sequence_order__lte=ctx.education_sequence)
        .filter(
            Q(career__max_education_level__isnull=True)
            | Q(career__max_education_level__sequence_order__gte=ctx.education_sequence)
        )
        .order_by("-weight_score", "career__career_name")
    )

    top_careers: list[dict[str, Any]] = []
    for m in career_rows:
        dscore = float(domain_score_by_id.get(m.domain_id, 0.0))
        mw = int(getattr(m, "weight_score", 0) or 0)
        cscore = (dscore * mw) / 100.0
        top_careers.append(
            {
                "id": str(m.career_id),
                "name": getattr(m.career, "career_name", "") or "",
                "score": round(float(cscore), 2),
                "reason": _career_reason(
                    domain_name=getattr(m.domain, "domain_name", "") or "your top domain",
                    mapping_weight=mw,
                    top_dim=top_dim,
                ),
            }
        )

    career_map: dict[str, dict[str, Any]] = {}
    for career in top_careers:
        cid = str(career.get("id") or "")
        if not cid:
            continue
        prev = career_map.get(cid)
        if not prev or float(career.get("score") or 0.0) > float(prev.get("score") or 0.0):
            career_map[cid] = career
    top_careers = list(career_map.values())
    top_careers.sort(key=lambda x: (-float(x["score"]), x["name"], x["id"]))
    top_careers = top_careers[:20]

    skill_mappings = list(
        DomainSkillMapping.objects.filter(
            domain_id__in=top_domain_pk_set,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        )
        .select_related("skill")
        .only("domain_id", "skill_id", "weight_score", "skill__skill_name")
    )

    required_weight_by_skill: dict[Any, int] = {}
    skill_name_by_id: dict[Any, str] = {}
    for m in skill_mappings:
        sid = m.skill_id
        w = int(getattr(m, "weight_score", 0) or 0)
        prev = required_weight_by_skill.get(sid, 0)
        if w > prev:
            required_weight_by_skill[sid] = w
        skill_name_by_id[sid] = getattr(m.skill, "skill_name", "") or ""

    user_skill_rows = list(
        UserSkill.objects.filter(
            user_id=user_id,
            deleted=False,
            is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        )
        .select_related("skill")
        .only("skill_id", "proficiency_score")
    )
    proficiency_by_skill: dict[Any, int] = {r.skill_id: int(r.proficiency_score) for r in user_skill_rows}

    def _gap_level(gap: int) -> str:
        if gap > 50:
            return "HIGH"
        if gap >= 20:
            return "MEDIUM"
        return "LOW"

    skill_gap_message = "ok"
    has_assessment = UserResponse.objects.filter(user_id=user_id, question__is_active=True).exists()
    if not user_skill_rows and not has_assessment:
        skill_gap_message = "Skill gap analysis requires further input. You can update your skills for better accuracy."

    gap_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    skill_gaps: list[dict[str, Any]] = []
    for sid, req_w in required_weight_by_skill.items():
        prof = proficiency_by_skill.get(sid)
        if prof is None:
            prof = _estimate_skill_proficiency_40_70(
                skill_name=skill_name_by_id.get(sid, "") or "",
                dim_scores=dim_scores,
            )
        gap = int(req_w) - int(prof)
        skill_gaps.append({"skill": skill_name_by_id.get(sid, "") or "", "gap_level": _gap_level(gap)})
    skill_gaps.sort(key=lambda x: (gap_rank.get(x["gap_level"], 99), x["skill"]))
    skill_gaps = skill_gaps[:50]

    if not top_careers:
        suggestion = ["Explore diploma programs", "Consider skill-based careers", "Improve your education level"]
        fallback_rows = list(
            Career.objects.filter(deleted=False, is_active=True)
            .select_related("min_education_level", "max_education_level")
            .filter(
                Q(min_education_level__isnull=True)
                | Q(min_education_level__sequence_order__lte=ctx.education_sequence)
            )
            .filter(
                Q(max_education_level__isnull=True)
                | Q(max_education_level__sequence_order__gte=ctx.education_sequence)
            )
            .only("id", "career_name")
            .order_by("career_name")[:10]
        )
        top_careers = [
            {
                "id": str(c.pk),
                "name": getattr(c, "career_name", "") or "",
                "score": 0.0,
                "reason": "Suggested starter path based on your current education level.",
            }
            for c in fallback_rows
        ]
        confidence = _calc_confidence(
            top_domain_score=float(top_domains[0]["score"]) if top_domains else 0.0,
            domain_count=len(top_domains),
            career_count=len(top_careers),
            has_assessment=has_assessment,
        )
        return {
            "message": "Based on your current education level, we recommend exploring foundational paths or upgrading qualifications.",
            "suggestion": suggestion,
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": skill_gaps,
            "confidence": confidence,
            "recommendation_type": "career",
            "education_level": ctx.education_level_code,
        }

    confidence = _calc_confidence(
        top_domain_score=float(top_domains[0]["score"]) if top_domains else 0.0,
        domain_count=len(top_domains),
        career_count=len(top_careers),
        has_assessment=has_assessment,
    )
    return {
        "message": skill_gap_message,
        "suggestion": [],
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
        "confidence": confidence,
        "recommendation_type": "career",
        "education_level": ctx.education_level_code,
    }


class RecommendationEngineService:
    def recommend(
        self,
        *,
        user_id: int,
        education_level_code: str | None = None,
        stream_code: str | None = None,
    ) -> dict[str, Any]:
        return generate_recommendation(
            user_id=user_id,
            education_level_code=education_level_code,
            stream_code=stream_code,
        )



def _career_reason(*, domain_name: str, mapping_weight: int, top_dim: str) -> str:
    dim_label = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality",
        "work_style": "work style",
    }.get(top_dim, top_dim)
    if mapping_weight >= 80:
        alignment = "strong"
    elif mapping_weight >= 60:
        alignment = "good"
    else:
        alignment = "moderate"
    return f"From {domain_name}: {alignment} fit and driven by your {dim_label}"


def _calc_confidence(*, top_domain_score: float, domain_count: int, career_count: int, has_assessment: bool) -> int:
    """
    Simple, deterministic confidence heuristic.
    Output intentionally capped for UX stability.
    """
    base = 40.0 if has_assessment else 15.0
    base += min(35.0, float(top_domain_score) * 0.35)  # 0..35
    base += min(10.0, domain_count * 1.0)  # 0..10
    base += min(10.0, career_count * 0.5)  # 0..10
    return int(round(max(0.0, min(88.0, base))))


def _resolve_user_context(
    *,
    user_id: int,
    education_level_code: str | None = None,
    stream_code: str | None = None,
) -> _UserContext | None:
    profile = (
        UserProfile.objects.select_related("stream", "education_level")
        .filter(user_id=user_id)
        .first()
    )
    if not profile:
        return None

    if education_level_code:
        edu = (
            EducationLevel.objects.filter(
                level_code__iexact=education_level_code,
                is_active=True,
                deleted=False,
            )
            .only("id", "sequence_order", "level_code")
            .first()
        )
    else:
        edu = getattr(profile, "education_level", None)

    if stream_code:
        stream = (
            Stream.objects.filter(
                stream_code__iexact=stream_code,
                is_active=True,
                deleted=False,
            )
            .only("id", "stream_code")
            .first()
        )
    else:
        stream = getattr(profile, "stream", None)

    if not stream or not edu:
        return None

    if getattr(stream, "deleted", False) or not getattr(stream, "is_active", True):
        return None
    if getattr(edu, "deleted", False) or not getattr(edu, "is_active", True):
        return None

    seq = int(getattr(edu, "sequence_order", 0) or 0)
    level_code = (getattr(edu, "level_code", "") or "").lower() or None
    return _UserContext(user_id=user_id, stream_id=stream.pk, education_sequence=seq, education_level_code=level_code)


def generate_recommendation(
    *,
    user_id: int,
    education_level_code: str | None = None,
    stream_code: str | None = None,
) -> dict[str, Any]:
    User = get_user_model()
    if not User.objects.filter(pk=user_id).exists():
        return _empty("User not found.")

    ctx = _resolve_user_context(user_id=user_id, education_level_code=education_level_code, stream_code=stream_code)
    if ctx is None:
        return _empty("User profile missing required education_level or active stream.")

    dim_scores = _assessment_dimension_scores_0_100(user_id=user_id)
    base = _base_domain_score(dim_scores)
    top_dim, top_dim_score = _top_factor(dim_scores)

    stream_domain_rows = list(
        StreamDomainMapping.objects.filter(
            stream_id=ctx.stream_id,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
        )
        .select_related("domain")
        .only(
            "id",
            "weight_score",
            "domain__id",
            "domain__domain_name",
            "domain__future_relevance_score",
        )
    )
    if not stream_domain_rows:
        return _empty("No active stream→domain mappings found for this user.", education_level_code=ctx.education_level_code)

    domain_items: list[dict[str, Any]] = []
    domain_score_by_id: dict[Any, float] = {}
    for m in stream_domain_rows:
        d = m.domain
        mapping_weight = int(getattr(m, "weight_score", 0) or 0)
        final = (base * 0.6) + (mapping_weight * 0.4)
        domain_score_by_id[d.pk] = float(final)
        domain_items.append(
            {
                "id": str(d.pk),
                "name": getattr(d, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": _domain_reason(
                    top_dim=top_dim,
                    top_dim_score=top_dim_score,
                    mapping_weight=mapping_weight,
                    domain_future_relevance=getattr(d, "future_relevance_score", None),
                ),
            }
        )

    domain_items.sort(key=lambda x: (-float(x["score"]), x["name"], x["id"]))
    top_domains = domain_items[:10]
    top_domain_pk_set = {int(x["id"]) for x in top_domains if str(x.get("id") or "").isdigit()}

    career_rows = list(
        DomainCareerMapping.objects.filter(
            domain_id__in=top_domain_pk_set,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
            career__deleted=False,
            career__is_active=True,
            career__min_education_level__deleted=False,
            career__min_education_level__is_active=True,
        )
        .select_related(
            "domain",
            "career",
            "career__min_education_level",
            "career__max_education_level",
        )
        .filter(career__min_education_level__sequence_order__lte=ctx.education_sequence)
        .filter(
            Q(career__max_education_level__isnull=True)
            | Q(career__max_education_level__sequence_order__gte=ctx.education_sequence)
        )
        .order_by("-weight_score", "career__career_name")
    )

    top_careers: list[dict[str, Any]] = []
    for m in career_rows:
        dscore = float(domain_score_by_id.get(m.domain_id, 0.0))
        mw = int(getattr(m, "weight_score", 0) or 0)
        cscore = (dscore * mw) / 100.0
        top_careers.append(
            {
                "id": str(m.career_id),
                "name": getattr(m.career, "career_name", "") or "",
                "score": round(float(cscore), 2),
                "reason": _career_reason(
                    domain_name=getattr(m.domain, "domain_name", "") or "your top domain",
                    mapping_weight=mw,
                    top_dim=top_dim,
                ),
            }
        )

    career_map: dict[str, dict[str, Any]] = {}
    for career in top_careers:
        cid = str(career.get("id") or "")
        if not cid:
            continue
        prev = career_map.get(cid)
        if not prev or float(career.get("score") or 0.0) > float(prev.get("score") or 0.0):
            career_map[cid] = career
    top_careers = list(career_map.values())
    top_careers.sort(key=lambda x: (-float(x["score"]), x["name"], x["id"]))
    top_careers = top_careers[:20]

    skill_mappings = list(
        DomainSkillMapping.objects.filter(
            domain_id__in=top_domain_pk_set,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        )
        .select_related("skill")
        .only("domain_id", "skill_id", "weight_score", "skill__skill_name")
    )

    required_weight_by_skill: dict[Any, int] = {}
    skill_name_by_id: dict[Any, str] = {}
    for m in skill_mappings:
        sid = m.skill_id
        w = int(getattr(m, "weight_score", 0) or 0)
        prev = required_weight_by_skill.get(sid, 0)
        if w > prev:
            required_weight_by_skill[sid] = w
        skill_name_by_id[sid] = getattr(m.skill, "skill_name", "") or ""

    user_skill_rows = list(
        UserSkill.objects.filter(
            user_id=user_id,
            deleted=False,
            is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        )
        .select_related("skill")
        .only("skill_id", "proficiency_score")
    )
    proficiency_by_skill: dict[Any, int] = {r.skill_id: int(r.proficiency_score) for r in user_skill_rows}

    def _gap_level(gap: int) -> str:
        if gap > 50:
            return "HIGH"
        if gap >= 20:
            return "MEDIUM"
        return "LOW"

    skill_gap_message = "ok"
    has_assessment = UserResponse.objects.filter(user_id=user_id, question__is_active=True).exists()
    if not user_skill_rows and not has_assessment:
        skill_gap_message = "Skill gap analysis requires further input. You can update your skills for better accuracy."

    gap_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    skill_gaps: list[dict[str, Any]] = []
    for sid, req_w in required_weight_by_skill.items():
        prof = proficiency_by_skill.get(sid)
        if prof is None:
            prof = _estimate_skill_proficiency_40_70(
                skill_name=skill_name_by_id.get(sid, "") or "",
                dim_scores=dim_scores,
            )
        gap = int(req_w) - int(prof)
        skill_gaps.append({"skill": skill_name_by_id.get(sid, "") or "", "gap_level": _gap_level(gap)})
    skill_gaps.sort(key=lambda x: (gap_rank.get(x["gap_level"], 99), x["skill"]))
    skill_gaps = skill_gaps[:50]

    if not top_careers:
        suggestion = ["Explore diploma programs", "Consider skill-based careers", "Improve your education level"]
        fallback_rows = list(
            Career.objects.filter(deleted=False, is_active=True)
            .select_related("min_education_level", "max_education_level")
            .filter(
                Q(min_education_level__isnull=True)
                | Q(min_education_level__sequence_order__lte=ctx.education_sequence)
            )
            .annotate(
                weighted_sum=Sum(weighted_expr, output_field=FloatField()),
                max_possible=Sum(max_expr, output_field=FloatField()),
            )
            .only("id", "career_name")
            .order_by("career_name")[:10]
        )
        top_careers = [
            {
                "id": str(c.pk),
                "name": getattr(c, "career_name", "") or "",
                "score": 0.0,
                "reason": "Suggested starter path based on your current education level.",
            }
            for c in fallback_rows
        ]
        confidence = _calc_confidence(
            top_domain_score=float(top_domains[0]["score"]) if top_domains else 0.0,
            domain_count=len(top_domains),
            career_count=len(top_careers),
            has_assessment=has_assessment,
        )
        return {
            "message": "Based on your current education level, we recommend exploring foundational paths or upgrading qualifications.",
            "suggestion": suggestion,
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": skill_gaps,
            "confidence": confidence,
            "recommendation_type": "career",
            "education_level": ctx.education_level_code,
        }

    confidence = _calc_confidence(
        top_domain_score=float(top_domains[0]["score"]) if top_domains else 0.0,
        domain_count=len(top_domains),
        career_count=len(top_careers),
        has_assessment=has_assessment,
    )
    return {
        "message": skill_gap_message,
        "suggestion": [],
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
        "confidence": confidence,
        "recommendation_type": "career",
        "education_level": ctx.education_level_code,
    }


class RecommendationEngineService:
    """
    Unified engine:
    - Keeps legacy production behavior (stream/domain/career + counsellor + domain decisions)
    - Also returns deterministic `top_domains`/`top_careers`/`skill_gaps` for the Admin QA tool
      (via StreamDomain/DomainCareer/DomainSkill mappings), with optional overrides.
    """

    DOMAIN_DECISION_TOP_N = 3

    def recommend(
        self,
        *,
        user_id: int,
        education_level_code: str | None = None,
        stream_code: str | None = None,
    ) -> dict[str, Any]:
        level_code = (education_level_code or self._get_education_level_code(user_id) or "").lower() or None

        # Legacy, production-facing result (keeps response shape stable).
        if level_code in STREAM_RECOMMENDATION_LEVELS:
            result = self._recommend_streams(user_id=user_id)
        elif level_code in DOMAIN_RECOMMENDATION_LEVELS:
            result = self._recommend_domains_for_college(user_id=user_id)
        else:
            result = self._recommend_careers(user_id=user_id, level_code=level_code)
            result["education_level"] = level_code
            result["is_entry_level"] = level_code in ENTRY_CAREER_LEVELS

        # Deterministic QA-friendly outputs (non-breaking additive keys).
        qa_result = generate_recommendation(
            user_id=user_id,
            education_level_code=education_level_code,
            stream_code=stream_code,
        )
        for k in ("message", "suggestion", "top_domains", "top_careers", "skill_gaps"):
            result[k] = qa_result.get(k)

        # Ensure QA expects these.
        result["confidence"] = int(result.get("confidence") or qa_result.get("confidence") or 0)
        result["recommendation_type"] = result.get("recommendation_type") or qa_result.get("recommendation_type")
        result["education_level"] = result.get("education_level") or qa_result.get("education_level") or level_code

        # Counsellor messaging and domain decisions (legacy add-ons).
        top_domain = result.get("top_domain") or result.get("domain")
        result["counsellor"] = build_counsellor_message(
            level_code=result.get("education_level") or level_code,
            recommendation_type=result.get("recommendation_type"),
            top_stream=result.get("top_stream"),
            stream_ranking=result.get("stream_ranking", []),
            top_domain=top_domain,
            domain_ranking=result.get("domain_ranking", []),
            top_career=result.get("top_career"),
            career_scores=result.get("career_scores", {}),
            confidence=result.get("confidence", 0),
            is_entry_level=result.get("is_entry_level", False),
            override_reason=result.get("override_reason"),
        )

        if result.get("domain_ranking"):
            try:
                result["domain_decisions"] = self._evaluate_top_domain_decisions(
                    user_id=user_id,
                    domain_ranking=result["domain_ranking"],
                )
            except Exception:
                # Domain decisions are optional enrichment.
                pass

        return result

    def _recommend_streams(self, *, user_id: int) -> dict[str, Any]:
        weighted_expr = ExpressionWrapper((6.0 - F("score_value")) * F("question__signal_strength"), output_field=FloatField())
        max_expr = ExpressionWrapper(F("question__signal_strength") * 5.0, output_field=FloatField())
        rows = (
            UserResponse.objects.filter(
                user_id=user_id,
                question__mapped_streams__stream_code__in=TENTH_GRADE_STREAM_CODES,
                question__mapped_streams__is_active=True,
                question__mapped_streams__deleted=False,
            )
            .values(
                "question__mapped_streams__id",
                "question__mapped_streams__stream_code",
                "question__mapped_streams__stream_name",
            )
            .annotate(
                weighted_sum=Sum(weighted_expr, output_field=FloatField()),
                max_possible=Sum(max_expr, output_field=FloatField()),
            )
            .order_by("-weighted_sum")
        )

        stream_ranking: list[dict[str, Any]] = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            normalized = (weighted_sum / max_possible * 100.0) if max_possible > 0 else 0.0
            stream_ranking.append(
                {
                    "stream_id": str(row["question__mapped_streams__id"]),
                    "stream_code": row["question__mapped_streams__stream_code"],
                    "stream_name": row["question__mapped_streams__stream_name"],
                    "score": int(round(max(0.0, min(100.0, normalized)))),
                }
            )

        if not stream_ranking:
            return self._fallback_result(education_level=LEVEL_10TH)

        stream_ranking.sort(key=lambda s: -int(s.get("score") or 0))
        confidence = self._calc_confidence(stream_ranking, score_key="score")
        return {
            "education_level": LEVEL_10TH,
            "recommendation_type": "stream",
            "top_stream": stream_ranking[0]["stream_code"] if stream_ranking else None,
            "stream_ranking": stream_ranking,
            "domain_ranking": [],
            "career_scores": {},
            "top_career": None,
            "confidence": confidence,
        }

    def _recommend_domains_for_college(self, *, user_id: int) -> dict[str, Any]:
        domain_ranking = self._rank_domains(user_id=user_id)
        if not domain_ranking:
            return self._fallback_result(education_level=LEVEL_12TH)
        confidence = self._calc_confidence(domain_ranking)
        return {
            "education_level": LEVEL_12TH,
            "recommendation_type": "college_domain",
            "top_domain": domain_ranking[0]["domain_code"] if domain_ranking else None,
            "domain_ranking": domain_ranking,
            "career_scores": {},
            "top_career": None,
            "confidence": confidence,
        }

    def _recommend_careers(self, *, user_id: int, level_code: str | None = None) -> dict[str, Any]:
        domain_ranking = self._rank_domains(user_id=user_id)
        if not domain_ranking:
            return self._fallback_result()

        level_order = {
            "secondary": 2,
            "higher_secondary": 3,
            "iti": 4,
            "diploma": 5,
            "graduation": 6,
            "post_graduation": 7,
            "doctorate": 8,
            "professional": 9,
        }
        user_level_seq = level_order.get(level_code or "", 0)

        top_domain = None
        top_domain_override_reason = None
        for i, ranked in enumerate(domain_ranking[:5]):
            candidate = Domain.objects.filter(id=ranked["domain_id"], deleted=False, is_active=True).first()
            if candidate is None:
                continue
            career_qs = (
                DomainCareerMapping.objects.filter(
                    domain=candidate,
                    deleted=False,
                    is_active=True,
                    career__deleted=False,
                    career__is_active=True,
                )
                .select_related("career__min_education_level")
                .only("career_id", "weight_score", "career__career_name", "career__career_code", "career__min_education_level__level_code")
            )
            eligible = [
                m
                for m in career_qs
                if not getattr(m.career, "min_education_level", None)
                or user_level_seq == 0
                or level_order.get((m.career.min_education_level.level_code or "").lower(), 0) <= user_level_seq
            ]
            if eligible:
                if i > 0:
                    top_domain_override_reason = (
                        f"{domain_ranking[0]['domain_name']} scored highest but has no careers mapped at your level — "
                        f"showing {ranked['domain_name']} instead."
                    )
                top_domain = candidate
                break

        if top_domain is None:
            return self._fallback_result()

        generic_result = self._build_generic_result(top_domain=top_domain, domain_ranking=domain_ranking, level_code=level_code)
        if top_domain_override_reason:
            generic_result["override_reason"] = top_domain_override_reason

        # Keep legacy decision merge behavior.
        decision_results = self._evaluate_top_domain_decisions(user_id=user_id, domain_ranking=domain_ranking)
        top_domain_code = (top_domain.domain_code or "").strip().lower()
        top_decision = decision_results.get(top_domain_code) if isinstance(decision_results, dict) else None
        if top_decision:
            merged = dict(generic_result)
            merged.update(top_decision)
            merged["domain_ranking"] = domain_ranking
            merged["domain_decisions"] = decision_results
            merged["override_reason"] = generic_result.get("override_reason")
            return merged
        if decision_results:
            first_decision = next(iter(decision_results.values()))
            merged = dict(generic_result)
            merged.update(first_decision)
            merged["domain_ranking"] = domain_ranking
            merged["domain_decisions"] = decision_results
            merged["override_reason"] = generic_result.get("override_reason")
            return merged

        return generic_result

    def _get_education_level_code(self, user_id: int) -> str | None:
        try:
            profile = UserProfile.objects.select_related("education_level").get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return None
        edu = getattr(profile, "education_level", None)
        return (getattr(edu, "level_code", "") or "").lower() or None

    def _evaluate_top_domain_decisions(self, *, user_id: int, domain_ranking: list[dict]) -> dict[str, dict]:
        decisions: dict[str, dict] = {}
        for ranked_domain in domain_ranking[: self.DOMAIN_DECISION_TOP_N]:
            domain_code = (ranked_domain.get("domain_code") or "").strip().lower()
            if not domain_code or domain_code not in DOMAIN_CONFIG:
                continue
            domain_result = evaluate_domain(domain_code=domain_code, user_id=user_id)
            if domain_result:
                decisions[domain_code] = domain_result
        return decisions

    def _rank_domains(self, *, user_id: int) -> list[dict[str, Any]]:
        weighted_expr = ExpressionWrapper((6.0 - F("score_value")) * F("question__signal_strength"), output_field=FloatField())
        max_expr = ExpressionWrapper(F("question__signal_strength") * 5.0, output_field=FloatField())

        level_filter = models.Q(question__education_level__isnull=True)
        try:
            profile = UserProfile.objects.select_related("education_level").get(user_id=user_id)
            if getattr(profile, "education_level", None):
                level_filter = models.Q(question__education_level=profile.education_level) | models.Q(
                    question__education_level__isnull=True
                )
        except UserProfile.DoesNotExist:
            pass

        rows = (
            UserResponse.objects.filter(
                level_filter,
                user_id=user_id,
                question__mapped_domains__deleted=False,
                question__mapped_domains__is_active=True,
            )
            .values(
                "question__mapped_domains__id",
                "question__mapped_domains__domain_code",
                "question__mapped_domains__domain_name",
            )
            .annotate(
                weighted_sum=Sum(weighted_expr, output_field=FloatField()),
                max_possible=Sum(max_expr, output_field=FloatField()),
                question_count=Count("id", distinct=True),
            )
            .order_by("-weighted_sum", "-max_possible")
        )

        total_answered = UserResponse.objects.filter(level_filter, user_id=user_id).count()
        domain_ranking: list[dict[str, Any]] = []
        for row in rows:
            max_possible = float(row.get("max_possible") or 0.0)
            weighted_sum = float(row.get("weighted_sum") or 0.0)
            q_count = int(row.get("question_count") or 0)
            if max_possible <= 0:
                continue
            raw_score = (weighted_sum / max_possible) * 100.0
            coverage = min(1.0, q_count / max(1, total_answered * 0.20))
            adjusted = (raw_score * 0.60) + (raw_score * coverage * 0.40)
            domain_ranking.append(
                {
                    "domain_id": row["question__mapped_domains__id"],
                    "domain_code": row["question__mapped_domains__domain_code"],
                    "domain_name": row["question__mapped_domains__domain_name"],
                    "score": int(round(max(0.0, min(100.0, adjusted)))),
                    "question_count": q_count,
                    "_raw": raw_score,
                    "_weighted_sum": weighted_sum,
                }
            )

        domain_ranking.sort(key=lambda d: (-int(d["score"]), -int(d["question_count"]), -float(d["_raw"]), str(d["domain_code"])))
        for d in domain_ranking:
            d.pop("_raw", None)
            d.pop("_weighted_sum", None)
        return domain_ranking

    def _build_generic_result(self, *, top_domain: Domain, domain_ranking: list[dict], level_code: str | None = None) -> dict[str, Any]:
        top_domain_score = int(domain_ranking[0]["score"]) if domain_ranking else 0
        mappings_qs = (
            DomainCareerMapping.objects.filter(
                domain=top_domain,
                deleted=False,
                is_active=True,
                career__deleted=False,
                career__is_active=True,
            )
            .select_related("career", "career__min_education_level")
        )

        level_order = {
            "secondary": 2,
            "higher_secondary": 3,
            "iti": 4,
            "diploma": 5,
            "graduation": 6,
            "post_graduation": 7,
            "doctorate": 8,
            "professional": 9,
        }
        user_level_seq = level_order.get(level_code or "", 0)

        career_scores: dict[str, int] = {}
        for mapping in mappings_qs.order_by("-weight_score", "career__career_name"):
            career = mapping.career
            min_level = getattr(career, "min_education_level", None)
            if min_level:
                min_seq = level_order.get((min_level.level_code or "").lower(), 0)
                if user_level_seq > 0 and min_seq > user_level_seq:
                    continue
            key = getattr(career, "career_code", None) or str(career.id)
            score = int(round((int(getattr(mapping, "weight_score", 0) or 0) * top_domain_score) / 100.0))
            career_scores[key] = max(0, min(100, score))

        top_career = None
        if career_scores:
            top_career = max(career_scores.items(), key=lambda item: item[1])[0]

        confidence = self._calc_confidence(domain_ranking)
        return {
            "recommendation_type": "career",
            "domain": (top_domain.domain_code or "").lower(),
            "career_scores": career_scores,
            "top_career": top_career,
            "domain_ranking": domain_ranking,
            "confidence": confidence,
        }

    @staticmethod
    def _calc_confidence(ranking: list[dict], score_key: str = "score") -> int:
        if not ranking:
            return 0
        top_score = int(ranking[0].get(score_key, 0) or 0)
        q_count = int(ranking[0].get("question_count", 1) or 1)
        score_component = top_score * 0.70
        if len(ranking) > 1:
            gap = top_score - int(ranking[1].get(score_key, 0) or 0)
            separation = min(20, gap * 0.5)
        else:
            separation = 15
        coverage = min(15, q_count * 2.5)
        raw = score_component + separation + coverage
        return int(round(min(88, max(0, raw))))

    @staticmethod
    def _fallback_result(education_level: str | None = None) -> dict[str, Any]:
        return {
            "education_level": education_level,
            "recommendation_type": None,
            "domain": None,
            "top_stream": None,
            "top_domain": None,
            "career_scores": {},
            "top_career": None,
            "confidence": 0,
            "domain_ranking": [],
            "stream_ranking": [],
        }

