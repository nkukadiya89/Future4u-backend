from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Avg, Q

from assessment.models import Question, UserResponse
from assessment.services.counsellor_message_service import build_counsellor_message
from assessment.services.domain_config import DOMAIN_CONFIG, domain_has_config
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

# ── Education level codes ─────────────────────────────────────────────────────
# These match EducationLevel.level_code values in the DB.
# Used as routing keys — if a level_code changes in the DB, update here too.
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

# ── Fallback stream codes (used only if DB has no Stream records for that level) ─
_FALLBACK_STREAM_CODES: dict[str, set[str]] = {
    LEVEL_10TH: {
        "science",
        "commerce",
        "arts",
        "vocational",
        "sports",
        "fine_arts",
        "agriculture",
    },
    LEVEL_12TH: {"science", "commerce", "arts", "vocational", "sports", "fine_arts"},
}


def _get_tenth_grade_stream_codes() -> set[str]:
    """Load 10th-grade stream codes from DB; fall back to _FALLBACK_STREAM_CODES."""
    codes = set(
        Stream.objects.filter(
            education_level__level_code=LEVEL_10TH,
            is_active=True,
            deleted=False,
        ).values_list("stream_code", flat=True)
    )
    return codes if codes else _FALLBACK_STREAM_CODES[LEVEL_10TH]


def _get_level_next_steps_from_db(level_code: str) -> list[str]:
    """
    Load next-step suggestions from EducationLevel.next_step_* fields in DB.
    Falls back to empty list — no hardcoded strings.
    """
    try:
        obj = (
            EducationLevel.objects.filter(
                level_code=level_code, is_active=True, deleted=False
            )
            .only("next_step_1", "next_step_2", "next_step_3")
            .first()
        )
        if obj:
            return [
                s
                for s in [obj.next_step_1, obj.next_step_2, obj.next_step_3]
                if s and s.strip()
            ]
    except Exception:
        pass
    return []


def _get_level_fallback_message(level_code: str) -> str:
    """
    Load fallback message from EducationLevel.fallback_action in DB.
    Falls back to empty string — no hardcoded strings.
    """
    try:
        obj = (
            EducationLevel.objects.filter(
                level_code=level_code, is_active=True, deleted=False
            )
            .only("fallback_action")
            .first()
        )
        if obj and obj.fallback_action:
            return obj.fallback_action
    except Exception:
        pass
    return ""


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
        "recommendation_type": None,
        "education_level": education_level_code,
        "domain_scores": [],
        "dimension_scores": {d: 0.0 for d in DIMENSIONS},
        "score_breakdown": {},
        # Keys expected by tests and API consumers
        "domain_ranking": [],
        "stream_ranking": [],
        "top_career": None,
        "top_stream": None,
        "top_domain": None,
        "career_scores": {},
        "is_entry_level": False,
    }


def _normalize_1_5(value: float) -> float:
    # Step 1: normalized = (avg_score - 1) / 4  -> 0..1
    return max(0.0, min(1.0, (float(value) - 1.0) / 4.0))


def _to_0_100(value_0_1: float) -> float:
    return max(0.0, min(100.0, float(value_0_1) * 100.0))


def _assessment_dimension_scores_0_1(*, user_id: int) -> dict[str, float]:
    rows = (
        UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .values("question__dimension")
        .annotate(avg=Avg("score_value"))
    )
    by_dim: dict[str, float] = {d: 0.5 for d in DIMENSIONS}
    for r in rows:
        dim = r.get("question__dimension")
        if dim in DIMENSIONS and r.get("avg") is not None:
            by_dim[dim] = _normalize_1_5(float(r["avg"]))
    return by_dim


DOMAIN_DIM_WEIGHTS: dict[str, float] = {
    # Default dimension weights used when a Domain has no per-domain weights set.
    # Per-domain overrides are loaded from Domain.interest_weight / aptitude_weight etc.
    # Must sum to 1.0.
    "interest": 0.35,
    "aptitude": 0.30,
    "personality": 0.20,
    "work_style": 0.15,
}


def _get_domain_dim_weights(domain: Domain | None) -> dict[str, float]:
    """
    Return dimension weights for a domain.
    Uses per-domain weights from Domain model if all 4 are set; falls back to DOMAIN_DIM_WEIGHTS.
    """
    if domain is not None:
        w = {
            "interest": domain.interest_weight,
            "aptitude": domain.aptitude_weight,
            "personality": domain.personality_weight,
            "work_style": domain.work_style_weight,
        }
        if all(v is not None for v in w.values()):
            return {k: float(v) for k, v in w.items()}
    return DOMAIN_DIM_WEIGHTS


def _clamp_0_100(value: float) -> int:
    return int(round(max(0.0, min(100.0, float(value)))))


# ── Scoring formula constants ─────────────────────────────────────────────────
# Confidence formula weights: gap*GAP + spread*SPREAD + coverage*COVERAGE_SCALE
_CONF_GAP_WEIGHT: float = 0.6  # how much the top-vs-second gap contributes
_CONF_SPREAD_WEIGHT: float = 0.2  # how much overall score spread contributes
_CONF_COVERAGE_SCALE: float = 20.0  # coverage (0..1) scaled to 0..20 points

# Stream influence: final_domain_score = base * (1 + mapping_weight/100 * STREAM_INFLUENCE)
_STREAM_INFLUENCE: float = 0.2

# Conflict detection: if |interest - aptitude| > this, decision_type = "conflicted"
_CONFLICT_DIM_THRESHOLD: float = 40.0

# Exploratory detection: if gap < this AND spread < this, decision_type = "exploratory"
_EXPLORATORY_GAP_THRESHOLD: float = 10.0
_EXPLORATORY_SPREAD_THRESHOLD: float = 20.0

# Confidence penalty when decision_type is "conflicted"
_CONFLICT_CONFIDENCE_PENALTY: float = 0.7

# Skill proficiency heuristic range (UX spec: never show below 40 or above 70)
_SKILL_PROF_MIN: float = 40.0
_SKILL_PROF_MAX: float = 70.0


def _domain_score_0_1(
    *,
    dim_avgs_0_1: dict[str, float],
    dim_counts: dict[str, int],
    dim_weights: dict[str, float],
) -> float:
    """
    Step 2: Domain score on 0..1.
    Uses ONLY dimensions that have relevant questions for this domain.
    Weights come from per-domain config or global DOMAIN_DIM_WEIGHTS fallback.
    """
    total_w = 0.0
    total = 0.0
    for d in DIMENSIONS:
        if int(dim_counts.get(d, 0) or 0) <= 0:
            continue
        w = float(dim_weights.get(d, DOMAIN_DIM_WEIGHTS.get(d, 0.0)))
        total_w += w
        total += float(dim_avgs_0_1.get(d, 0.0)) * w
    return (total / total_w) if total_w > 0 else 0.0


def _calc_confidence(
    *,
    top_score_0_100: float,
    second_score_0_100: float,
    domain_scores_0_100: list[float],
    coverage_0_1: float,
) -> int:
    """
    Confidence formula:
      (gap * _CONF_GAP_WEIGHT) + (spread * _CONF_SPREAD_WEIGHT) + (coverage * _CONF_COVERAGE_SCALE)

    gap      = top score minus second score (how clear the winner is)
    spread   = max minus min across all domain scores (how differentiated the results are)
    coverage = fraction of active questions answered (0..1)
    """
    gap = float(top_score_0_100) - float(second_score_0_100)
    scores = [max(0.0, min(100.0, float(v))) for v in (domain_scores_0_100 or [])]
    spread = float(max(scores) - min(scores)) if scores else 0.0
    coverage = max(0.0, min(1.0, float(coverage_0_1)))
    confidence = (
        (gap * _CONF_GAP_WEIGHT)
        + (spread * _CONF_SPREAD_WEIGHT)
        + (coverage * _CONF_COVERAGE_SCALE)
    )
    return _clamp_0_100(confidence)


def _top_factor(scores: dict[str, float]) -> tuple[str, float]:
    best_dim = DIMENSIONS[0]
    best_val = float(scores.get(best_dim, 50.0))
    for d in DIMENSIONS[1:]:
        v = float(scores.get(d, 50.0))
        if v > best_val:
            best_dim, best_val = d, v
    return best_dim, best_val


def _load_domain_keywords() -> tuple[list[str], list[str]]:
    """
    Load all technical and domain keywords from DomainCounsellorKnowledge.
    Returns two flat deduplicated lists: (technical_keywords, domain_keywords).
    Returns empty lists if DB has no records — caller falls back to balanced formula.
    """
    try:
        from domain.models import DomainCounsellorKnowledge

        rows = DomainCounsellorKnowledge.objects.exclude(
            technical_keywords=[]
        ).values_list("technical_keywords", "domain_keywords")
        tech, dom = set(), set()
        for tk, dk in rows:
            tech.update(k.lower() for k in (tk or []) if k)
            dom.update(k.lower() for k in (dk or []) if k)
        return list(tech), list(dom)
    except Exception:
        pass
    return [], []


def _estimate_skill_proficiency_40_70(
    *, skill_name: str, dim_scores: dict[str, float]
) -> int:
    """
    Heuristic skill proficiency estimator when UserSkill is missing.
    Reads keywords from DomainCounsellorKnowledge in DB.
    Keeps output within 40–70 range as per UX spec.
    """
    name = (skill_name or "").strip().lower()
    aptitude = float(dim_scores.get("aptitude", 50.0))
    interest = float(dim_scores.get("interest", 50.0))
    personality = float(dim_scores.get("personality", 50.0))
    work_style = float(dim_scores.get("work_style", 50.0))

    technical_keywords, domain_keywords = _load_domain_keywords()

    if any(k in name for k in technical_keywords):
        basis = aptitude
    elif any(k in name for k in domain_keywords):
        basis = interest
    else:
        basis = (
            (aptitude * 0.45)
            + (interest * 0.45)
            + (personality * 0.05)
            + (work_style * 0.05)
        )

    return int(
        round(
            max(
                _SKILL_PROF_MIN,
                min(
                    _SKILL_PROF_MAX,
                    _SKILL_PROF_MIN
                    + (float(basis) / 100.0) * (_SKILL_PROF_MAX - _SKILL_PROF_MIN),
                ),
            )
        )
    )


def _domain_reason(
    *,
    top_dim: str,
    top_dim_score: float,
    mapping_weight: int,
    domain_future_relevance: int | None,
) -> str:
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


def _career_reason(*, top_dimension: str, top_domains: list[str]) -> str:
    # Step 7: remove static/fake messaging.
    dim_label = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality",
        "work_style": "work style",
    }.get(top_dimension, top_dimension)
    domains = ", ".join([d for d in top_domains if d][:3])
    return f"Based on your high {dim_label} and strong alignment with {domains}"


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

    if not edu:
        return None

    level_code_resolved = (getattr(edu, "level_code", "") or "").lower() or None

    # For stream-recommendation levels (e.g. 10th grade), stream is not required —
    # the engine recommends which stream to pick, so the user hasn't chosen one yet.
    if not stream and level_code_resolved not in STREAM_RECOMMENDATION_LEVELS:
        return None

    if stream and (
        getattr(stream, "deleted", False) or not getattr(stream, "is_active", True)
    ):
        return None
    if getattr(edu, "deleted", False) or not getattr(edu, "is_active", True):
        return None

    seq = int(getattr(edu, "sequence_order", 0) or 0)
    level_code = (getattr(edu, "level_code", "") or "").lower() or None
    return _UserContext(
        user_id=user_id,
        stream_id=stream.pk if stream else None,
        education_sequence=seq,
        education_level_code=level_code,
    )


def generate_recommendation(
    *,
    user_id: int,
    education_level_code: str | None = None,
    stream_code: str | None = None,
) -> dict[str, Any]:
    User = get_user_model()
    if not User.objects.filter(pk=user_id).exists():
        return _empty("User not found.")

    ctx = _resolve_user_context(
        user_id=user_id,
        education_level_code=education_level_code,
        stream_code=stream_code,
    )
    if ctx is None:
        return _empty("User profile missing required education_level or active stream.")

    # STEP 1: dimension normalization (0..1)
    dim_scores_0_1 = _assessment_dimension_scores_0_1(user_id=user_id)
    dim_scores_0_100 = {
        d: round(_to_0_100(dim_scores_0_1.get(d, 0.5)), 2) for d in DIMENSIONS
    }
    top_dim, top_dim_score = _top_factor(dim_scores_0_100)

    # Shared assessment coverage metric (0..1)
    answered = UserResponse.objects.filter(
        user_id=user_id, question__is_active=True
    ).count()
    total_active = max(1, Question.objects.filter(is_active=True).count())
    coverage = float(answered) / float(total_active)

    # STREAM recommendation pipeline (single source of truth)
    if ctx.education_level_code in STREAM_RECOMMENDATION_LEVELS:
        responses = list(
            UserResponse.objects.filter(
                user_id=user_id,
                question__is_active=True,
                question__mapped_streams__stream_code__in=_get_tenth_grade_stream_codes(),
                question__mapped_streams__is_active=True,
                question__mapped_streams__deleted=False,
            )
            .select_related("question")
            .prefetch_related("question__mapped_streams")
        )

        streams_by_qid: dict[int, list[Any]] = {}
        stream_codes = _get_tenth_grade_stream_codes()
        sums: dict[int, float] = {}
        counts: dict[int, int] = {}
        meta: dict[int, dict[str, Any]] = {}
        for r in responses:
            q = getattr(r, "question", None)
            if not q:
                continue
            qid = int(getattr(q, "id", 0) or 0)
            if qid <= 0:
                continue

            if qid not in streams_by_qid:
                streams_by_qid[qid] = sorted(
                    [
                        s
                        for s in list(getattr(q, "mapped_streams", []).all())
                        if getattr(s, "stream_code", None) in stream_codes
                        and getattr(s, "is_active", True)
                        and not getattr(s, "deleted", False)
                    ],
                    key=lambda s: int(getattr(s, "id", 0) or 0),
                )
            streams = streams_by_qid[qid]
            if not streams:
                continue

            n = len(streams)
            contrib = _normalize_1_5(float(getattr(r, "score_value", 0) or 0)) / float(
                n
            )
            for s in streams:
                sid = int(s.id)
                sums[sid] = float(sums.get(sid, 0.0)) + float(contrib)
                counts[sid] = int(counts.get(sid, 0) or 0) + 1
                meta[sid] = {
                    "stream_code": getattr(s, "stream_code", None),
                    "stream_name": getattr(s, "stream_name", None),
                }

        stream_ranking: list[dict[str, Any]] = []
        for sid, ssum in sums.items():
            c = int(counts.get(sid, 0) or 0)
            if c <= 0:
                continue
            score_0_100 = _to_0_100(float(ssum) / float(c))
            stream_ranking.append(
                {
                    "stream_id": str(sid),
                    "stream_code": meta.get(sid, {}).get("stream_code"),
                    "stream_name": meta.get(sid, {}).get("stream_name"),
                    "score": round(float(score_0_100), 2),
                }
            )

        stream_ranking.sort(
            key=lambda s: (
                -float(s.get("score") or 0.0),
                str(s.get("stream_name") or ""),
                str(s.get("stream_id") or ""),
            )
        )
        top_stream_score = (
            float(stream_ranking[0].get("score") or 0.0) if stream_ranking else 0.0
        )
        second_stream_score = (
            float(stream_ranking[1].get("score") or 0.0)
            if len(stream_ranking) > 1
            else 0.0
        )
        spread = (
            (
                max([float(s.get("score") or 0.0) for s in stream_ranking])
                - min([float(s.get("score") or 0.0) for s in stream_ranking])
            )
            if stream_ranking
            else 0.0
        )
        gap = top_stream_score - second_stream_score
        confidence = _calc_confidence(
            top_score_0_100=top_stream_score,
            second_score_0_100=second_stream_score,
            domain_scores_0_100=[float(s.get("score") or 0.0) for s in stream_ranking],
            coverage_0_1=coverage,
        )
        interest = float(dim_scores_0_100.get("interest", 0.0))
        aptitude = float(dim_scores_0_100.get("aptitude", 0.0))
        if abs(interest - aptitude) > _CONFLICT_DIM_THRESHOLD:
            decision_type = "conflicted"
        elif (
            gap < _EXPLORATORY_GAP_THRESHOLD and spread < _EXPLORATORY_SPREAD_THRESHOLD
        ):
            decision_type = "exploratory"
        else:
            decision_type = "confident"
        if decision_type == "conflicted":
            confidence = _clamp_0_100(float(confidence) * _CONFLICT_CONFIDENCE_PENALTY)

        result: dict[str, Any] = {
            "message": (
                "ok"
                if stream_ranking
                else "Complete more assessment questions for a clearer stream recommendation."
            ),
            "suggestion": [],
            "top_domains": [],
            "top_careers": [],
            "skill_gaps": [],
            "confidence": confidence,
            "decision_type": decision_type,
            "signals": {
                "top_dimension": top_dim,
                "strongest_domains": [],
                "decision_type": decision_type,
            },
            "recommendation_type": "stream" if stream_ranking else None,
            "education_level": ctx.education_level_code,
            "domain_scores": [],
            "dimension_scores": dim_scores_0_100,
            "score_breakdown": {
                "formulae": {
                    "dimension_normalization": "normalized=(avg_score-1)/4",
                    "confidence": f"gap*{_CONF_GAP_WEIGHT} + spread*{_CONF_SPREAD_WEIGHT} + coverage*{_CONF_COVERAGE_SCALE}",
                }
            },
            # Legacy-facing keys (single pipeline output)
            "top_stream": (
                stream_ranking[0].get("stream_code") if stream_ranking else None
            ),
            "stream_ranking": stream_ranking,
            "top_domain": None,
            "domain_ranking": [],
            "career_scores": {},
            "top_career": None,
            "is_entry_level": False,
        }
        result["counsellor"] = build_counsellor_message(
            level_code=result.get("education_level"),
            recommendation_type=result.get("recommendation_type"),
            top_stream=result.get("top_stream"),
            stream_ranking=result.get("stream_ranking", []),
            top_domain=None,
            domain_ranking=[],
            top_career=None,
            career_scores={},
            confidence=result.get("confidence", 0),
            is_entry_level=False,
            override_reason=None,
        )
        return result

    # Stream → domain mapping weights (soft influence).
    # stream_id can be None for stream-recommendation levels (10th grade) — handled above.
    # For career/domain levels without a stream, fall back to the assessment engine
    # which scores domains directly from question mappings (no stream dependency).
    if not ctx.stream_id:
        from assessment.services.recommendation_engine_service import (
            RecommendationEngineService as AssessmentEngine,
        )

        result = AssessmentEngine().recommend(user_id=user_id)
        # Ensure all expected keys are present
        result.setdefault("domain_ranking", [])
        result.setdefault("stream_ranking", [])
        result.setdefault("top_career", None)
        result.setdefault("top_stream", None)
        result.setdefault("top_domain", result.get("domain"))
        result.setdefault("career_scores", {})
        result.setdefault("is_entry_level", False)
        result.setdefault("domain_scores", [])
        result.setdefault("dimension_scores", {d: 0.0 for d in DIMENSIONS})
        result.setdefault("score_breakdown", {})
        return result

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
            "domain__domain_code",
            "domain__future_relevance_score",
            "domain__interest_weight",
            "domain__aptitude_weight",
            "domain__personality_weight",
            "domain__work_style_weight",
        )
    )
    if not stream_domain_rows:
        return _empty(
            "No active stream→domain mappings found for this user.",
            education_level_code=ctx.education_level_code,
        )

    # STEP 2 + 3: per-domain signals (normalized + leakage fix)
    responses = list(
        UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .select_related("question")
        .prefetch_related("question__mapped_domains")
    )
    domains_by_qid: dict[int, list[Any]] = {}
    sums: dict[int, dict[str, float]] = {}
    counts: dict[int, dict[str, int]] = {}
    for r in responses:
        q = getattr(r, "question", None)
        if not q:
            continue
        dim = getattr(q, "dimension", None)
        if dim not in DIMENSIONS:
            continue
        qid = int(getattr(q, "id", 0) or 0)
        if qid <= 0:
            continue
        if qid not in domains_by_qid:
            domains_by_qid[qid] = sorted(
                [
                    d
                    for d in list(getattr(q, "mapped_domains", []).all())
                    if getattr(d, "is_active", True)
                    and not getattr(d, "deleted", False)
                ],
                key=lambda d: int(getattr(d, "id", 0) or 0),
            )
        domains = domains_by_qid[qid]
        if not domains:
            continue
        n = len(domains)
        contrib = _normalize_1_5(float(getattr(r, "score_value", 0) or 0)) / float(n)
        for d in domains:
            did = int(d.id)
            sums.setdefault(did, {}).setdefault(dim, 0.0)
            counts.setdefault(did, {}).setdefault(dim, 0)
            sums[did][dim] += float(contrib)
            counts[did][dim] += 1

    domain_scores: list[dict[str, Any]] = []
    domain_score_by_id_0_1: dict[int, float] = {}
    breakdown_domains: dict[str, Any] = {}
    for m in stream_domain_rows:
        dom = m.domain
        did = int(dom.id)
        mapping_weight = int(getattr(m, "weight_score", 0) or 0)

        dim_avgs_0_1 = {}
        dim_counts = {}
        for d in DIMENSIONS:
            c = int(counts.get(did, {}).get(d, 0) or 0)
            dim_counts[d] = c
            if c > 0:
                dim_avgs_0_1[d] = float(sums.get(did, {}).get(d, 0.0)) / float(c)
            else:
                dim_avgs_0_1[d] = 0.0

        base_domain_score = _domain_score_0_1(
            dim_avgs_0_1=dim_avgs_0_1,
            dim_counts=dim_counts,
            dim_weights=_get_domain_dim_weights(dom),
        )

        # STEP 4: apply stream weight (soft influence)
        multiplier = 1.0 + (float(mapping_weight) / 100.0) * _STREAM_INFLUENCE
        # Stability: clamp overflow + avoid flooring when base is zero.
        if float(base_domain_score) == 0.0:
            final_domain_score = 0.0
        else:
            final_domain_score = min(1.0, float(base_domain_score) * float(multiplier))
            final_domain_score = max(0.02, float(final_domain_score))
        domain_score_by_id_0_1[did] = final_domain_score

        domain_scores.append(
            {
                "id": str(did),
                "name": getattr(dom, "domain_name", "") or "",
                "code": getattr(dom, "domain_code", "") or "",
                "score": round(_to_0_100(final_domain_score), 2),
                "reason": _domain_reason(
                    top_dim=top_dim,
                    top_dim_score=float(top_dim_score),
                    mapping_weight=mapping_weight,
                    domain_future_relevance=getattr(
                        dom, "future_relevance_score", None
                    ),
                ),
            }
        )
        breakdown_domains[str(did)] = {
            "domain_name": getattr(dom, "domain_name", "") or "",
            "dimension_avgs_0_1": {
                d: round(float(dim_avgs_0_1.get(d, 0.0)), 4) for d in DIMENSIONS
            },
            "dimension_counts": {d: int(dim_counts.get(d, 0) or 0) for d in DIMENSIONS},
            "base_domain_score_0_1": round(float(base_domain_score), 6),
            "stream_mapping_weight": mapping_weight,
            "stream_multiplier": round(float(multiplier), 6),
            "final_domain_score_0_1": round(float(final_domain_score), 6),
        }

    domain_scores.sort(key=lambda x: (-float(x["score"]), str(x["name"]), str(x["id"])))
    top_domains = domain_scores[:10]
    top_domain_ids = {
        int(d["id"]) for d in top_domains if str(d.get("id") or "").isdigit()
    }

    # STEP 6: confidence
    top_score = float(top_domains[0]["score"]) if top_domains else 0.0
    second_score = float(top_domains[1]["score"]) if len(top_domains) > 1 else 0.0
    all_domain_scores_0_100 = [float(d.get("score") or 0.0) for d in domain_scores]
    spread = (
        (max(all_domain_scores_0_100) - min(all_domain_scores_0_100))
        if all_domain_scores_0_100
        else 0.0
    )
    gap = top_score - second_score
    confidence = _calc_confidence(
        top_score_0_100=top_score,
        second_score_0_100=second_score,
        domain_scores_0_100=all_domain_scores_0_100,
        coverage_0_1=coverage,
    )
    interest = float(dim_scores_0_100.get("interest", 0.0))
    aptitude = float(dim_scores_0_100.get("aptitude", 0.0))
    if abs(interest - aptitude) > _CONFLICT_DIM_THRESHOLD:
        decision_type = "conflicted"
    elif gap < _EXPLORATORY_GAP_THRESHOLD and spread < _EXPLORATORY_SPREAD_THRESHOLD:
        decision_type = "exploratory"
    else:
        decision_type = "confident"
    if decision_type == "conflicted":
        confidence = _clamp_0_100(float(confidence) * _CONFLICT_CONFIDENCE_PENALTY)

    # STEP 5: career scoring (non-linear) + normalization
    career_rows = list(
        DomainCareerMapping.objects.filter(
            domain_id__in=top_domain_ids,
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
        .order_by("career__career_name", "career_id", "domain_id")
    )

    raw: list[dict[str, Any]] = []
    for m in career_rows:
        did = int(m.domain_id)
        dscore = float(domain_score_by_id_0_1.get(did, 0.0))
        mw = int(getattr(m, "weight_score", 0) or 0)
        cscore = math.sqrt(max(0.0, dscore)) * (float(mw) / 100.0)
        raw.append(
            {
                "career_id": str(m.career_id),
                "career_name": getattr(m.career, "career_name", "") or "",
                "domain_id": str(did),
                "domain_name": getattr(m.domain, "domain_name", "") or "",
                "mw": mw,
                "cscore": cscore,
            }
        )

    # Deduplicate careers by best cscore
    best: dict[str, dict[str, Any]] = {}
    for r in raw:
        cid = r["career_id"]
        prev = best.get(cid)
        if prev is None or float(r["cscore"]) > float(prev["cscore"]):
            best[cid] = r

    domain_counts: dict[str, int] = {}
    for r in best.values():
        did = str(r.get("domain_id") or "")
        domain_counts[did] = int(domain_counts.get(did, 0) or 0) + 1

    adjusted_cscore_by_cid: dict[str, float] = {}
    for cid, r in best.items():
        did = str(r.get("domain_id") or "")
        denom = float(domain_counts.get(did, 1) or 1)
        adjusted_cscore_by_cid[cid] = float(r.get("cscore") or 0.0) / denom

    total_cscore = float(sum(float(v) for v in adjusted_cscore_by_cid.values()))
    careers_scored: list[dict[str, Any]] = []
    breakdown_careers: dict[str, Any] = {}
    for cid, r in best.items():
        adj = float(adjusted_cscore_by_cid.get(cid, 0.0))
        score = (adj / float(total_cscore) * 100.0) if total_cscore > 0 else 0.0
        careers_scored.append(
            {
                "id": cid,
                "name": r["career_name"],
                "score": round(float(score), 2),
                "domain_id": r["domain_id"],
                "domain_name": r["domain_name"],
            }
        )
        breakdown_careers[cid] = {
            "career_name": r["career_name"],
            "domain_id": r["domain_id"],
            "domain_name": r["domain_name"],
            "final_domain_score_0_1": round(
                float(domain_score_by_id_0_1.get(int(r["domain_id"]), 0.0)), 6
            ),
            "career_mapping_weight": int(r["mw"]),
            "cscore": round(float(r["cscore"]), 8),
            "domain_career_count": int(
                domain_counts.get(str(r.get("domain_id") or ""), 1) or 1
            ),
            "adjusted_cscore": round(float(adj), 8),
            "total_cscore": round(float(total_cscore), 8),
            "career_score_0_100": round(float(score), 4),
        }

    careers_scored.sort(
        key=lambda x: (-float(x["score"]), str(x["name"]), str(x["id"]))
    )

    # STEP 8: enforce diversity (max 2 careers per domain)
    top_careers: list[dict[str, Any]] = []
    per_domain: dict[str, int] = {}
    for c in careers_scored:
        dom_id = str(c.get("domain_id") or "")
        if per_domain.get(dom_id, 0) >= 2:
            continue
        top_careers.append(
            {
                "id": c["id"],
                "name": c["name"],
                "score": c["score"],
                "reason": _career_reason(
                    top_dimension=top_dim, top_domains=[d["name"] for d in top_domains]
                ),
            }
        )
        per_domain[dom_id] = per_domain.get(dom_id, 0) + 1
        if len(top_careers) >= 20:
            break

    top_domain_pk_set = top_domain_ids

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
    proficiency_by_skill: dict[Any, int] = {
        r.skill_id: int(r.proficiency_score) for r in user_skill_rows
    }

    def _gap_level(gap: int) -> str:
        if gap > 50:
            return "HIGH"
        if gap >= 20:
            return "MEDIUM"
        return "LOW"

    skill_gap_message = "ok"
    has_assessment = UserResponse.objects.filter(
        user_id=user_id, question__is_active=True
    ).exists()
    if not user_skill_rows and not has_assessment:
        skill_gap_message = "Skill gap analysis requires further input. You can update your skills for better accuracy."

    gap_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    skill_gaps: list[dict[str, Any]] = []
    for sid, req_w in required_weight_by_skill.items():
        prof = proficiency_by_skill.get(sid)
        if prof is None:
            prof = _estimate_skill_proficiency_40_70(
                skill_name=skill_name_by_id.get(sid, "") or "",
                dim_scores=dim_scores_0_100,
            )
        gap = int(req_w) - int(prof)
        skill_gaps.append(
            {"skill": skill_name_by_id.get(sid, "") or "", "gap_level": _gap_level(gap)}
        )
    skill_gaps.sort(key=lambda x: (gap_rank.get(x["gap_level"], 99), x["skill"]))
    skill_gaps = skill_gaps[:50]

    if not top_careers:
        # Load next steps from DB (EducationLevel.next_step_*) — no hardcoded strings.
        suggestion = _get_level_next_steps_from_db(ctx.education_level_code or "")
        fallback_rows = list(
            Career.objects.filter(deleted=False, is_active=True)
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
                "reason": _career_reason(
                    top_dimension=top_dim, top_domains=[d["name"] for d in top_domains]
                ),
            }
            for c in fallback_rows
        ]
        return {
            "message": _get_level_fallback_message(ctx.education_level_code or ""),
            "suggestion": suggestion,
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": skill_gaps,
            "confidence": confidence,
            "decision_type": decision_type,
            "signals": {
                "top_dimension": top_dim,
                "strongest_domains": [
                    d.get("name") for d in top_domains[:3] if d.get("name")
                ],
                "decision_type": decision_type,
            },
            "recommendation_type": "career",
            "education_level": ctx.education_level_code,
            "domain_scores": domain_scores,
            "dimension_scores": dim_scores_0_100,
            "score_breakdown": {
                "domains": breakdown_domains,
                "careers": breakdown_careers,
                "formulae": {
                    "dimension_normalization": "normalized=(avg_score-1)/4",
                    "domain_score": f"interest*{DOMAIN_DIM_WEIGHTS['interest']} + aptitude*{DOMAIN_DIM_WEIGHTS['aptitude']} + personality*{DOMAIN_DIM_WEIGHTS['personality']} + work_style*{DOMAIN_DIM_WEIGHTS['work_style']} (reweighted by available dims; per-domain overrides apply)",
                    "multi_domain_leakage": "contribution_per_domain = value/N",
                    "stream_influence": f"final = domain_score * (1 + mapping_weight/100*{_STREAM_INFLUENCE})",
                    "career": "cscore=sqrt(dscore)*(mw/100); career_score=(cscore/sum(cscores))*100",
                    "confidence": f"gap*{_CONF_GAP_WEIGHT} + spread*{_CONF_SPREAD_WEIGHT} + coverage*{_CONF_COVERAGE_SCALE}",
                    "diversity": "max 2 careers per domain",
                },
            },
            # Legacy-facing keys (single pipeline output)
            "top_stream": None,
            "stream_ranking": [],
            "top_domain": (top_domains[0].get("name") if top_domains else None),
            "domain_ranking": [
                {
                    "domain_id": int(d["id"]),
                    "domain_code": d.get("code") or None,
                    "domain_name": d.get("name"),
                    "score": _clamp_0_100(float(d.get("score") or 0.0)),
                    "question_count": None,
                }
                for d in top_domains
                if str(d.get("id") or "").isdigit()
            ],
            "career_scores": {
                c["id"]: _clamp_0_100(float(c.get("score") or 0.0))
                for c in top_careers
                if c.get("id")
            },
            "top_career": (top_careers[0].get("id") if top_careers else None),
            "is_entry_level": (ctx.education_level_code in ENTRY_CAREER_LEVELS),
        }

    result = {
        "message": skill_gap_message,
        "suggestion": [],
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
        "confidence": confidence,
        "decision_type": decision_type,
        "signals": {
            "top_dimension": top_dim,
            "strongest_domains": [
                d.get("name") for d in top_domains[:3] if d.get("name")
            ],
            "decision_type": decision_type,
        },
        "recommendation_type": "career",
        "education_level": ctx.education_level_code,
        "domain_scores": domain_scores,
        "dimension_scores": dim_scores_0_100,
        "score_breakdown": {
            "domains": breakdown_domains,
            "careers": breakdown_careers,
            "formulae": {
                "dimension_normalization": "normalized=(avg_score-1)/4",
                "domain_score": f"interest*{DOMAIN_DIM_WEIGHTS['interest']} + aptitude*{DOMAIN_DIM_WEIGHTS['aptitude']} + personality*{DOMAIN_DIM_WEIGHTS['personality']} + work_style*{DOMAIN_DIM_WEIGHTS['work_style']} (reweighted by available dims; per-domain overrides apply)",
                "multi_domain_leakage": "contribution_per_domain = value/N",
                "stream_influence": f"final = domain_score * (1 + mapping_weight/100*{_STREAM_INFLUENCE})",
                "career": "cscore=sqrt(dscore)*(mw/100); career_score=(cscore/sum(cscores))*100",
                "confidence": f"gap*{_CONF_GAP_WEIGHT} + spread*{_CONF_SPREAD_WEIGHT} + coverage*{_CONF_COVERAGE_SCALE}",
                "diversity": "max 2 careers per domain",
            },
        },
    }
    # Legacy-facing keys (single pipeline output)
    result["top_stream"] = None
    result["stream_ranking"] = []
    result["top_domain"] = top_domains[0].get("name") if top_domains else None
    result["domain_ranking"] = [
        {
            "domain_id": int(d["id"]),
            "domain_code": d.get("code") or None,
            "domain_name": d.get("name"),
            "score": _clamp_0_100(float(d.get("score") or 0.0)),
            "question_count": None,
        }
        for d in top_domains
        if str(d.get("id") or "").isdigit()
    ]
    result["career_scores"] = {
        c["id"]: _clamp_0_100(float(c.get("score") or 0.0))
        for c in top_careers
        if c.get("id")
    }
    result["top_career"] = top_careers[0].get("id") if top_careers else None
    result["is_entry_level"] = ctx.education_level_code in ENTRY_CAREER_LEVELS
    result["counsellor"] = build_counsellor_message(
        level_code=result.get("education_level"),
        recommendation_type=result.get("recommendation_type"),
        top_stream=None,
        stream_ranking=[],
        top_domain=result.get("top_domain"),
        domain_ranking=result.get("domain_ranking", []),
        top_career=result.get("top_career"),
        career_scores=result.get("career_scores", {}),
        confidence=result.get("confidence", 0),
        is_entry_level=result.get("is_entry_level", False),
        override_reason=None,
    )
    if result.get("domain_ranking"):
        try:
            result[
                "domain_decisions"
            ] = RecommendationEngineService()._evaluate_top_domain_decisions(
                user_id=user_id,
                domain_ranking=result["domain_ranking"],
            )
        except Exception:
            pass
    return result


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
        # Single pipeline only: no merging, no dual-system conflict.
        return generate_recommendation(
            user_id=user_id,
            education_level_code=education_level_code,
            stream_code=stream_code,
        )

    def _get_education_level_code(self, user_id: int) -> str | None:
        try:
            profile = UserProfile.objects.select_related("education_level").get(
                user_id=user_id
            )
        except UserProfile.DoesNotExist:
            return None
        edu = getattr(profile, "education_level", None)
        return (getattr(edu, "level_code", "") or "").lower() or None

    def _evaluate_top_domain_decisions(
        self, *, user_id: int, domain_ranking: list[dict]
    ) -> dict[str, dict]:
        decisions: dict[str, dict] = {}
        for ranked_domain in domain_ranking[: self.DOMAIN_DECISION_TOP_N]:
            domain_code = (ranked_domain.get("domain_code") or "").strip().lower()
            if not domain_code or not domain_has_config(domain_code):
                continue
            domain_result = evaluate_domain(domain_code=domain_code, user_id=user_id)
            if domain_result:
                decisions[domain_code] = domain_result
        return decisions

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
