from __future__ import annotations

from django.db import models
from django.db.models import Count, F, FloatField, Sum
from django.db.models.expressions import ExpressionWrapper

from assessment.models import UserResponse
from assessment.services.counsellor_message_service import build_counsellor_message
from assessment.services.domain_config import DOMAIN_CONFIG
from assessment.services.universal_scoring_service import evaluate_domain
from domain.models import Domain
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from education_level.models import EducationLevel
from stream.models import Stream
from stream_domain_mapping.models import StreamDomainMapping
from user_profile.models import UserProfile
from user_skill.models import UserSkill


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

TENTH_GRADE_STREAM_CODES = {
    "science", "commerce", "arts", "vocational",
    "sports", "fine_arts", "agriculture",
}

TENTH_GRADE_STREAM_CODES = {
    "science",
    "commerce",
    "arts",
    "vocational",
    "sports",
    "fine_arts",
    "agriculture",
}


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
    Education-level aware recommendation engine.
    - 10th  -> stream recommendations
    - 12th  -> domain/field recommendations
    - ITI/Diploma -> entry-level career + domain
    - Grad/PG/PhD/Professional -> full career + domain
    """

    DOMAIN_DECISION_TOP_N = 3

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
    def recommend(
        self,
        *,
        user_id: int,
        education_level_code: str | None = None,
        stream_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Stable API used by admin QA tooling.
        Overrides are not persisted; they only affect the calculation.
        """
        return generate_recommendation(
            user_id=user_id,
            education_level_code=education_level_code,
            stream_code=stream_code,
        )

