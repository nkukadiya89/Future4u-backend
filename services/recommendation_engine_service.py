from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count

from assessment.models import UserResponse
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from stream_domain_mapping.models import StreamDomainMapping
from user_profile.models import UserProfile
from user_skill.models import UserSkill

logger = logging.getLogger(__name__)


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

# These match EducationLevel.sequence_order values.
SEQ_10TH = 2
SEQ_12TH = 3
SEQ_ITI = 4
SEQ_DIPLOMA = 5
SEQ_GRADUATION = 6
SEQ_POST_GRAD = 7
SEQ_DOCTORATE = 8
SEQ_PROFESSIONAL = 9


def _domain_affinity_from_domain(domain) -> dict[str, float] | None:
    iw = getattr(domain, "interest_weight", None)
    aw = getattr(domain, "aptitude_weight", None)
    pw = getattr(domain, "personality_weight", None)
    ww = getattr(domain, "work_style_weight", None)
    if any(v is None for v in (iw, aw, pw, ww)):
        return None
    return {
        "interest": float(iw),
        "aptitude": float(aw),
        "personality": float(pw),
        "work_style": float(ww),
    }


@dataclass(frozen=True)
class _UserContext:
    user_id: int
    stream_id: Any
    stream_code: str
    education_sequence: int


def _empty(message: str) -> dict[str, Any]:
    return {
        "message": message,
        "tier": "unknown",
        "recommended_streams": [],
        "top_domains": [],
        "top_careers": [],
        "skill_gaps": [],
        "next_step": None,
    }


def _score_1_5_to_0_100(value: float) -> float:
    return max(0.0, min(100.0, ((value - 1.0) / 4.0) * 100.0))


def _assessment_dimension_scores(*, user_id: int) -> dict[str, float]:
    by_dim: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    resp_rows = (
        UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .values("question__dimension", "score_value", "question__signal_strength")
    )
    sums: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    weights: dict[str, float] = {d: 0.0 for d in DIMENSIONS}

    for row in resp_rows:
        dim = row.get("question__dimension")
        if dim not in DIMENSIONS:
            continue
        try:
            score = float(row.get("score_value") or 0.0)
            weight = float(row.get("question__signal_strength") or 1.0)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            weight = 1.0
        sums[dim] += score * weight
        weights[dim] += weight

    for dim in DIMENSIONS:
        if weights[dim] <= 0:
            continue
        avg_1_5 = sums[dim] / weights[dim]
        by_dim[dim] = _score_1_5_to_0_100(avg_1_5)

    return by_dim


def _assessment_confidence(*, user_id: int, target_per_dimension: int = 5) -> tuple[dict[str, float], float]:
    answered = {
        row["question__dimension"]: int(row["answered"] or 0)
        for row in UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .values("question__dimension")
        .annotate(answered=Count("id"))
    }
    target = max(1, int(target_per_dimension))
    by_dim = {d: min(1.0, answered.get(d, 0) / target) for d in DIMENSIONS}
    overall = sum(by_dim.values()) / len(DIMENSIONS)
    return by_dim, overall


def _top_factor(scores: dict[str, float]) -> tuple[str, float]:
    best = max(DIMENSIONS, key=lambda d: scores.get(d, 0.0))
    return best, scores.get(best, 0.0)


def _gap_level(gap: int) -> str:
    if gap > 50:
        return "HIGH"
    if gap >= 20:
        return "MEDIUM"
    return "LOW"


def _estimate_proficiency(*, skill_name: str, dim_scores: dict[str, float]) -> int:
    name = (skill_name or "").lower()
    aptitude = dim_scores.get("aptitude", 0.0)
    interest = dim_scores.get("interest", 0.0)
    technical = ("python", "sql", "data", "cloud", "network", "program", "coding", "ai", "ml", "devops", "linux", "api")
    domain_keywords = ("marketing", "finance", "design", "health", "medical", "communication", "writing", "business", "management")
    if any(keyword in name for keyword in technical):
        basis = aptitude
    elif any(keyword in name for keyword in domain_keywords):
        basis = interest
    else:
        basis = (
            aptitude * 0.45
            + interest * 0.45
            + dim_scores.get("personality", 0.0) * 0.05
            + dim_scores.get("work_style", 0.0) * 0.05
        )

    if sum(dim_scores.get(d, 0.0) for d in DIMENSIONS) == 0.0:
        return 50
    return int(round(max(40.0, min(70.0, 40.0 + (basis / 100.0) * 30.0))))


def _fetch_context(*, user_id: int) -> _UserContext | None:
    profile = UserProfile.objects.select_related("stream", "education_level").filter(user_id=user_id).first()
    if not profile:
        return None

    education_level = getattr(profile, "education_level", None)
    if not education_level:
        return None
    if getattr(education_level, "deleted", False) or not getattr(education_level, "is_active", True):
        return None

    sequence = int(getattr(education_level, "sequence_order", 0) or 0)
    stream = getattr(profile, "stream", None)
    if stream and (getattr(stream, "deleted", False) or not getattr(stream, "is_active", True)):
        stream = None

    if sequence > SEQ_10TH and not stream:
        return None

    return _UserContext(
        user_id=user_id,
        stream_id=stream.pk if stream else None,
        stream_code=(getattr(stream, "stream_code", "") or "") if stream else "",
        education_sequence=sequence,
    )


_VALID_12TH_STREAMS = {
    "science",
    "commerce",
    "arts",
    "vocational",
    "fine_arts",
    "sports",
    "agriculture",
}

_DIM_STREAM_AFFINITY: dict[str, list[str]] = {
    "aptitude": ["science", "commerce"],
    "interest": ["arts", "fine_arts", "sports"],
    "personality": ["arts", "fine_arts"],
    "work_style": ["vocational", "agriculture"],
}


def _recommend_streams(*, dim_scores: dict[str, float]) -> list[dict[str, Any]]:
    from stream.models import Stream

    all_streams = {
        stream.stream_code: stream
        for stream in Stream.objects.filter(
            is_active=True,
            deleted=False,
            stream_code__in=_VALID_12TH_STREAMS,
        )
    }

    stream_scores: dict[str, float] = {}
    stream_dim_count: dict[str, int] = {}
    for dim, codes in _DIM_STREAM_AFFINITY.items():
        dim_value = dim_scores.get(dim, 0.0)
        for code in codes:
            if code in _VALID_12TH_STREAMS:
                stream_scores[code] = stream_scores.get(code, 0.0) + dim_value
                stream_dim_count[code] = stream_dim_count.get(code, 0) + 1

    for code, score in list(stream_scores.items()):
        stream_scores[code] = round(score / max(1, stream_dim_count.get(code, 1)), 2)

    for code in _VALID_12TH_STREAMS:
        stream_scores.setdefault(code, 0.0)

    top_dim = max(DIMENSIONS, key=lambda d: dim_scores.get(d, 0.0))
    dim_display = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality",
        "work_style": "work style",
    }
    results: list[dict[str, Any]] = []
    for code, score in sorted(stream_scores.items(), key=lambda item: -item[1]):
        stream = all_streams.get(code)
        if not stream:
            continue
        driving_dims = [dim for dim, codes in _DIM_STREAM_AFFINITY.items() if code in codes]
        stream_top_dim = max(driving_dims, key=lambda d: dim_scores.get(d, 0.0)) if driving_dims else top_dim
        results.append(
            {
                "stream_code": code,
                "stream_name": stream.stream_name,
                "score": round(score, 2),
                "description": getattr(stream, "description", "") or "",
                "traditional_equivalent": getattr(stream, "traditional_equivalent", "") or "",
                "reason": f"Suits your {dim_display.get(stream_top_dim, stream_top_dim)} strength",
            }
        )
    return results[:6]


def _domain_fit_score(
    *,
    affinity: dict[str, float] | None,
    dim_scores: dict[str, float],
    stream_weight: int,
    confidence_overall: float = 1.0,
    stream_bias: float = 0.30,
) -> float:
    confidence_overall = max(0.0, min(1.0, float(confidence_overall)))
    if affinity:
        fit_assessment = sum(dim_scores.get(dim, 0.0) * weight for dim, weight in affinity.items())
    else:
        fit_assessment = sum(dim_scores.get(dim, 0.0) for dim in DIMENSIONS) / len(DIMENSIONS)

    fit = (confidence_overall * fit_assessment) + ((1.0 - confidence_overall) * 50.0)
    return (fit * (1.0 - stream_bias)) + (stream_weight * stream_bias)


def _score_domains_from_stream_codes(
    *,
    stream_codes: list[str],
    dim_scores: dict[str, float],
    confidence_overall: float,
) -> tuple[list[dict[str, Any]], dict[Any, float], set[Any]]:
    rows = list(
        StreamDomainMapping.objects.filter(
            stream__stream_code__in=stream_codes,
            deleted=False,
            is_active=True,
            stream__deleted=False,
            stream__is_active=True,
            domain__deleted=False,
            domain__is_active=True,
        )
        .select_related("domain")
        .only(
            "weight_score",
            "domain__id",
            "domain__domain_name",
            "domain__domain_code",
            "domain__future_relevance_score",
            "domain__suggested_degrees",
            "domain__counselor_note",
            "domain__interest_weight",
            "domain__aptitude_weight",
            "domain__personality_weight",
            "domain__work_style_weight",
        )
    )
    if not rows:
        return [], {}, set()

    best_stream_weight_by_domain: dict[Any, int] = {}
    domain_ref: dict[Any, Any] = {}
    for mapping in rows:
        domain_id = mapping.domain_id
        weight = int(getattr(mapping, "weight_score", 0) or 0)
        if weight > best_stream_weight_by_domain.get(domain_id, 0):
            best_stream_weight_by_domain[domain_id] = weight
            domain_ref[domain_id] = mapping.domain

    items: list[dict[str, Any]] = []
    top_pk_by_id: dict[str, Any] = {}
    score_by_id: dict[Any, float] = {}
    for domain_id, stream_weight in best_stream_weight_by_domain.items():
        domain = domain_ref[domain_id]
        final = _domain_fit_score(
            affinity=_domain_affinity_from_domain(domain),
            dim_scores=dim_scores,
            stream_weight=stream_weight,
            confidence_overall=confidence_overall,
            stream_bias=0.60,
        )
        score_by_id[domain_id] = float(final)
        items.append(
            {
                "id": str(domain_id),
                "name": getattr(domain, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": getattr(domain, "counselor_note", "") or f"{getattr(domain, 'domain_name', 'This field')} could be a great fit for you.",
                "suggested_degrees": getattr(domain, "suggested_degrees", "") or "",
            }
        )
        top_pk_by_id[str(domain_id)] = domain_id

    items.sort(key=lambda item: (-item["score"], item["name"]))
    top = items[:10]
    top_domain_pk_set = {top_pk_by_id[item["id"]] for item in top if item["id"] in top_pk_by_id}
    return top, score_by_id, top_domain_pk_set


def _score_domains(
    *,
    ctx: _UserContext,
    dim_scores: dict[str, float],
    confidence_overall: float,
) -> tuple[list[dict[str, Any]], dict[Any, float], set[Any]]:
    rows = list(
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
            "domain__domain_code",
            "domain__future_relevance_score",
            "domain__suggested_degrees",
            "domain__counselor_note",
            "domain__interest_weight",
            "domain__aptitude_weight",
            "domain__personality_weight",
            "domain__work_style_weight",
        )
    )
    if not rows:
        return [], {}, set()

    items: list[dict[str, Any]] = []
    score_by_id: dict[Any, float] = {}
    for mapping in rows:
        domain = mapping.domain
        stream_weight = int(getattr(mapping, "weight_score", 0) or 0)
        final = _domain_fit_score(
            affinity=_domain_affinity_from_domain(domain),
            dim_scores=dim_scores,
            stream_weight=stream_weight,
            confidence_overall=confidence_overall,
        )
        score_by_id[domain.pk] = float(final)
        items.append(
            {
                "id": str(domain.pk),
                "name": getattr(domain, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": getattr(domain, "counselor_note", "") or f"{getattr(domain, 'domain_name', 'This field')} could be a great fit for you.",
                "suggested_degrees": getattr(domain, "suggested_degrees", "") or "",
            }
        )

    items.sort(key=lambda item: (-item["score"], item["name"]))
    top = items[:10]
    top_id_set = {item["id"] for item in top}
    pk_set = {mapping.domain.pk for mapping in rows if str(mapping.domain.pk) in top_id_set}
    return top, score_by_id, pk_set


def _score_careers(
    *,
    top_domain_pk_set: set[Any],
    domain_score_by_id: dict[Any, float],
    edu_seq: int,
    filter_by_edu: bool,
    min_edu_seq: int = 0,
) -> list[dict[str, Any]]:
    career_filter: dict[str, Any] = {
        "domain_id__in": top_domain_pk_set,
        "deleted": False,
        "is_active": True,
        "domain__deleted": False,
        "domain__is_active": True,
        "career__deleted": False,
        "career__is_active": True,
    }
    if filter_by_edu:
        career_filter["career__min_education_level__sequence_order__lte"] = edu_seq
    if min_edu_seq > 0:
        career_filter["career__min_education_level__sequence_order__gte"] = min_edu_seq

    rows = list(
        DomainCareerMapping.objects.filter(**career_filter)
        .select_related("domain", "career", "career__min_education_level")
        .order_by("-weight_score", "career__career_name")
    )

    career_map: dict[str, dict[str, Any]] = {}
    for mapping in rows:
        domain_score = float(domain_score_by_id.get(mapping.domain_id, 0.0))
        mapping_weight = int(getattr(mapping, "weight_score", 0) or 0)
        career_score = (domain_score * mapping_weight) / 100.0
        entry = {
            "id": str(mapping.career_id),
            "name": getattr(mapping.career, "career_name", "") or "",
            "description": getattr(mapping.career, "description", "") or "",
            "domain": getattr(mapping.domain, "domain_name", "") or "",
            "score": round(career_score, 2),
        }
        career_id = entry["id"]
        if career_id not in career_map or career_score > career_map[career_id]["score"]:
            career_map[career_id] = entry

    result = sorted(career_map.values(), key=lambda item: (-item["score"], item["name"]))
    return result[:20]


def _score_skill_gaps(*, top_domain_pk_set: set[Any], user_id: int, dim_scores: dict[str, float]) -> list[dict[str, str]]:
    skill_rows = list(
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
        .only("skill_id", "weight_score", "skill__skill_name")
    )

    required_weight: dict[Any, int] = {}
    skill_names: dict[Any, str] = {}
    for mapping in skill_rows:
        skill_id = mapping.skill_id
        weight = int(getattr(mapping, "weight_score", 0) or 0)
        if weight > required_weight.get(skill_id, 0):
            required_weight[skill_id] = weight
        skill_names[skill_id] = getattr(mapping.skill, "skill_name", "") or ""

    user_skills = {
        row.skill_id: int(row.proficiency_score)
        for row in UserSkill.objects.filter(
            user_id=user_id,
            deleted=False,
            is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        ).only("skill_id", "proficiency_score")
    }

    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "UNKNOWN": 3}
    gaps: list[dict[str, str]] = []
    for skill_id, required in required_weight.items():
        if skill_id in user_skills:
            level = _gap_level(required - user_skills[skill_id])
        elif user_skills:
            estimated = _estimate_proficiency(skill_name=skill_names.get(skill_id, ""), dim_scores=dim_scores)
            level = _gap_level(required - estimated)
        else:
            level = "UNKNOWN"
        gaps.append({"skill": skill_names.get(skill_id, ""), "gap_level": level})

    gaps.sort(key=lambda item: (rank.get(item["gap_level"], 99), item["skill"]))
    return gaps[:50]


def generate_recommendation(user_id: int, *, ctx_override: _UserContext | None = None) -> dict[str, Any]:
    user_model = get_user_model()
    if not user_model.objects.filter(pk=user_id).exists():
        logger.warning("generate_recommendation: user_id=%s not found", user_id)
        return _empty("User not found.")

    ctx = ctx_override or _fetch_context(user_id=user_id)
    if ctx is None:
        logger.info("generate_recommendation: user_id=%s missing profile/stream", user_id)
        return _empty("Complete your profile (education level + stream) to get recommendations.")

    dim_scores = _assessment_dimension_scores(user_id=user_id)
    _, confidence_overall = _assessment_confidence(user_id=user_id, target_per_dimension=5)
    seq = ctx.education_sequence

    if seq <= SEQ_10TH:
        recommended_streams = _recommend_streams(dim_scores=dim_scores)
        stream_codes = [item.get("stream_code") for item in recommended_streams if item.get("stream_code")]
        top_domains, domain_score_by_id, top_domain_pk_set = _score_domains_from_stream_codes(
            stream_codes=stream_codes,
            dim_scores=dim_scores,
            confidence_overall=confidence_overall,
        )
        top_careers = (
            _score_careers(
                top_domain_pk_set=top_domain_pk_set,
                domain_score_by_id=domain_score_by_id,
                edu_seq=seq,
                filter_by_edu=False,
            )
            if top_domain_pk_set
            else []
        )
        return {
            "tier": "10th",
            "message": "Based on your answers, here are the best streams for you to pick in 11th-12th grade. Do not worry, you do not need to decide your final career now. This just shows possible directions.",
            "recommended_streams": recommended_streams[:4],
            "top_domains": top_domains[:4],
            "top_careers": top_careers[:6],
            "skill_gaps": [],
            "next_step": "After 10th, choose your 11th-12th stream. Then come back and take the full assessment to get career recommendations.",
        }

    if seq == SEQ_12TH:
        top_domains, domain_score_by_id, top_domain_pk_set = _score_domains(
            ctx=ctx,
            dim_scores=dim_scores,
            confidence_overall=confidence_overall,
        )
        if not top_domains:
            return _empty("No domain mappings found for your stream.")
        top_careers = _score_careers(
            top_domain_pk_set=top_domain_pk_set,
            domain_score_by_id=domain_score_by_id,
            edu_seq=seq,
            filter_by_edu=False,
        )
        return {
            "tier": "12th",
            "message": "Based on your stream and assessment, here are the best fields to explore for college.",
            "recommended_streams": [],
            "top_domains": top_domains,
            "top_careers": top_careers[:5],
            "skill_gaps": [],
            "next_step": "Choose a degree based on your top fields. During your college journey, you will get personalized skill and career recommendations.",
        }

    if seq in (SEQ_ITI, SEQ_DIPLOMA):
        top_domains, domain_score_by_id, top_domain_pk_set = _score_domains(
            ctx=ctx,
            dim_scores=dim_scores,
            confidence_overall=confidence_overall,
        )
        if not top_domains:
            return _empty("No domain mappings found for your stream.")

        top_careers = _score_careers(
            top_domain_pk_set=top_domain_pk_set,
            domain_score_by_id=domain_score_by_id,
            edu_seq=seq,
            filter_by_edu=True,
        )
        skill_gaps = _score_skill_gaps(
            top_domain_pk_set=top_domain_pk_set,
            user_id=user_id,
            dim_scores=dim_scores,
        )

        domains_with_careers = {career["domain"] for career in top_careers}
        top_domains = [domain for domain in top_domains if domain["name"] in domains_with_careers] or top_domains[:4]
        qualification_name = "ITI / Vocational" if seq == SEQ_ITI else "Diploma"
        has_assessment = UserResponse.objects.filter(user_id=user_id, question__is_active=True).exists()
        message = (
            f"Here are domains, careers, and skill priorities suited to your {qualification_name} profile."
            if has_assessment
            else f"Here are stream-aligned domains and careers for your {qualification_name} profile. Complete the assessment for stronger skill insights."
        )
        return {
            "tier": qualification_name.lower().replace(" / ", "_").replace(" ", "_"),
            "message": message,
            "recommended_streams": [],
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": skill_gaps,
            "next_step": "Build the core skills for your top domains and consider advancing into higher qualifications when it fits your plan.",
        }

    top_domains, domain_score_by_id, top_domain_pk_set = _score_domains(
        ctx=ctx,
        dim_scores=dim_scores,
        confidence_overall=confidence_overall,
    )
    if not top_domains:
        return _empty("No domain mappings found for your stream.")

    top_careers = _score_careers(
        top_domain_pk_set=top_domain_pk_set,
        domain_score_by_id=domain_score_by_id,
        edu_seq=seq,
        filter_by_edu=True,
        min_edu_seq=SEQ_GRADUATION,
    )
    skill_gaps = _score_skill_gaps(
        top_domain_pk_set=top_domain_pk_set,
        user_id=user_id,
        dim_scores=dim_scores,
    )

    has_assessment = UserResponse.objects.filter(user_id=user_id, question__is_active=True).exists()
    tier_names = {
        SEQ_GRADUATION: "graduation",
        SEQ_POST_GRAD: "post_graduation",
        SEQ_DOCTORATE: "doctorate",
        SEQ_PROFESSIONAL: "professional",
    }
    return {
        "tier": tier_names.get(seq, "advanced"),
        "message": (
            "Here are your personalised domain, career and skill recommendations."
            if has_assessment
            else "Complete the assessment for more accurate recommendations."
        ),
        "recommended_streams": [],
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
        "next_step": "Focus on building skills in your top domains and explore internships or projects to get started.",
    }
