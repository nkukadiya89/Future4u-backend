from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Avg, Q

from assessment.models import UserResponse
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from stream_domain_mapping.models import StreamDomainMapping
from user_profile.models import UserProfile
from user_skill.models import UserSkill


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")


@dataclass(frozen=True)
class _UserContext:
    user_id: int
    stream_id: Any
    education_sequence: int


def _empty(message: str) -> dict[str, Any]:
    return {
        "message": message,
        "top_domains": [],
        "top_careers": [],
        "skill_gaps": [],
    }


def _score_1_5_to_0_100(value: float) -> float:
    # 1 -> 0, 3 -> 50, 5 -> 100
    return max(0.0, min(100.0, ((value - 1.0) / 4.0) * 100.0))


def _assessment_dimension_scores_0_100(*, user_id: int) -> dict[str, float]:
    # UserResponse has no is_active/deleted flags; we can only filter via Question.is_active.
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


def _fetch_user_context(*, user_id: int) -> _UserContext | None:
    # UserProfile has no is_active/deleted; validate referenced masters for safety.
    profile = (
        UserProfile.objects.select_related("stream", "education_level")
        .filter(user_id=user_id)
        .first()
    )
    if not profile:
        return None
    stream = getattr(profile, "stream", None)
    edu = getattr(profile, "education_level", None)
    if not stream or not edu:
        return None
    if getattr(stream, "deleted", False) or not getattr(stream, "is_active", True):
        return None
    if getattr(edu, "deleted", False) or not getattr(edu, "is_active", True):
        return None
    seq = int(getattr(edu, "sequence_order", 0) or 0)
    return _UserContext(user_id=user_id, stream_id=stream.pk, education_sequence=seq)


def generate_recommendation(user_id: int) -> dict[str, Any]:
    """
    Production-grade, deterministic recommendation generator.

    Constraints:
    - No model changes
    - Enforce is_active=True AND deleted=False wherever available
    - Never crash: always returns structured response
    """
    User = get_user_model()
    if not User.objects.filter(pk=user_id).exists():
        return _empty("User not found.")

    ctx = _fetch_user_context(user_id=user_id)
    if ctx is None:
        return _empty("User profile missing required education_level or active stream.")

    dim_scores = _assessment_dimension_scores_0_100(user_id=user_id)
    base = _base_domain_score(dim_scores)
    top_dim, top_dim_score = _top_factor(dim_scores)

    # STEP 3: Stream -> Domain mappings (strict filters across mapping + domain master)
    stream_domain_qs = (
        StreamDomainMapping.objects.filter(
            stream_id=ctx.stream_id,
            deleted=False,
            is_active=True,
            domain__deleted=False,
            domain__is_active=True,
        )
        .select_related("domain")
        .only("id", "weight_score", "is_primary", "domain__id", "domain__domain_name", "domain__future_relevance_score")
    )
    stream_domain_rows = list(stream_domain_qs)
    if not stream_domain_rows:
        return _empty("No active stream→domain mappings found for this user.")

    # STEP 4: Domain scoring
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
    top_domain_ids = [x["id"] for x in top_domains]
    top_domain_pk_set = set([m.domain.pk for m in stream_domain_rows if str(m.domain.pk) in set(top_domain_ids)])

    # STEP 5/6: Domain -> Careers (batch, strict filters, education eligibility)
    career_qs = (
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
        .filter(
            career__min_education_level__sequence_order__lte=ctx.education_sequence,
        )
        .filter(
            Q(career__max_education_level__isnull=True)
            | Q(career__max_education_level__sequence_order__gte=ctx.education_sequence)
        )
        .order_by("-weight_score", "career__career_name")
    )
    career_rows = list(career_qs)
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
    top_careers.sort(key=lambda x: (-float(x["score"]), x["name"], x["id"]))
    top_careers = top_careers[:20]

    # STEP 7/8: Domain -> Skills and skill gaps
    skill_map_qs = (
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
    skill_mappings = list(skill_map_qs)

    required_weight_by_skill: dict[Any, int] = {}
    skill_name_by_id: dict[Any, str] = {}
    for m in skill_mappings:
        sid = m.skill_id
        w = int(getattr(m, "weight_score", 0) or 0)
        prev = required_weight_by_skill.get(sid, 0)
        if w > prev:
            required_weight_by_skill[sid] = w
        skill_name_by_id[sid] = getattr(m.skill, "skill_name", "") or ""

    user_skill_qs = (
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
    user_skill_rows = list(user_skill_qs)
    proficiency_by_skill: dict[Any, int] = {r.skill_id: int(r.proficiency_score) for r in user_skill_rows}

    def _gap_level(gap: int | None) -> str:
        if gap is None:
            return "UNKNOWN"
        if gap > 50:
            return "HIGH"
        if gap >= 20:
            return "MEDIUM"
        return "LOW"

    gap_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
    skill_gaps: list[dict[str, Any]] = []
    for sid, req_w in required_weight_by_skill.items():
        prof = proficiency_by_skill.get(sid)
        gap = None if prof is None else int(req_w) - int(prof)
        level = _gap_level(gap)
        skill_gaps.append(
            {
                "skill": skill_name_by_id.get(sid, "") or "",
                "gap_level": level,
            }
        )
    skill_gaps.sort(key=lambda x: (gap_rank.get(x["gap_level"], 99), x["skill"]))
    skill_gaps = skill_gaps[:50]

    return {
        "message": "ok",
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
    }

