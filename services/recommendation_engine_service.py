from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count

from assessment.models import Question, UserResponse
from domain_career_mapping.models import DomainCareerMapping
from domain_skill_mapping.models import DomainSkillMapping
from stream_domain_mapping.models import StreamDomainMapping
from user_profile.models import UserProfile
from user_skill.models import UserSkill


DIMENSIONS = ("interest", "aptitude", "personality", "work_style")

# ── Education tiers ────────────────────────────────────────────────────────────
TIER_10TH = 2
TIER_12TH = 3
TIER_DIPLOMA = 5
TIER_GRADUATE = 6

def _domain_affinity_from_domain(domain) -> dict[str, float] | None:
    """
    Domain-level affinity weights are now stored in the DB (Domain master).
    If weights are not configured, return None and callers will fall back to equal weights.
    """
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


# ── Scoring helpers ────────────────────────────────────────────────────────────


def _score_1_5_to_0_100(value: float) -> float:
    return max(0.0, min(100.0, ((value - 1.0) / 4.0) * 100.0))


def _assessment_dimension_scores(*, user_id: int) -> dict[str, float]:
    rows = (
        UserResponse.objects.filter(user_id=user_id, question__is_active=True)
        .values("question__dimension")
        .annotate(avg=Avg("score_value"), answered=Count("id"))
    )
    totals = {
        r["dimension"]: r["total"]
        for r in Question.objects.filter(is_active=True)
        .values("dimension")
        .annotate(total=Count("id"))
    }
    by_dim: dict[str, float] = {d: 0.0 for d in DIMENSIONS}
    for r in rows:
        dim = r.get("question__dimension")
        if dim not in DIMENSIONS or r.get("avg") is None:
            continue
        raw = _score_1_5_to_0_100(float(r["avg"]))
        answered = int(r.get("answered") or 0)
        total = int(totals.get(dim) or 1)
        by_dim[dim] = raw * (answered / total)
    return by_dim


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
    technical = (
        "python",
        "sql",
        "data",
        "cloud",
        "network",
        "program",
        "coding",
        "ai",
        "ml",
        "devops",
        "linux",
        "api",
    )
    domain_kw = (
        "marketing",
        "finance",
        "design",
        "health",
        "medical",
        "communication",
        "writing",
        "business",
        "management",
    )
    if any(k in name for k in technical):
        basis = aptitude
    elif any(k in name for k in domain_kw):
        basis = interest
    else:
        basis = (
            aptitude * 0.45
            + interest * 0.45
            + dim_scores.get("personality", 0.0) * 0.05
            + dim_scores.get("work_style", 0.0) * 0.05
        )
    # If user has no assessment data at all, default to neutral (50) not minimum (40)
    total_signal = sum(dim_scores.get(d, 0.0) for d in DIMENSIONS)
    if total_signal == 0.0:
        return 50
    return int(round(max(40.0, min(70.0, 40.0 + (basis / 100.0) * 30.0))))


def _fetch_context(*, user_id: int) -> _UserContext | None:
    profile = (
        UserProfile.objects.select_related("stream", "education_level")
        .filter(user_id=user_id)
        .first()
    )
    if not profile:
        return None
    edu = getattr(profile, "education_level", None)
    if not edu:
        return None
    if getattr(edu, "deleted", False) or not getattr(edu, "is_active", True):
        return None
    seq = int(getattr(edu, "sequence_order", 0) or 0)

    stream = getattr(profile, "stream", None)
    if stream and (
        getattr(stream, "deleted", False) or not getattr(stream, "is_active", True)
    ):
        stream = None

    # seq > TIER_10TH means they've chosen a stream — it's required from 12th onwards
    if seq > TIER_10TH and not stream:
        return None

    return _UserContext(
        user_id=user_id,
        stream_id=stream.pk if stream else None,
        stream_code=getattr(stream, "stream_code", "") or "" if stream else "",
        education_sequence=seq,
    )


# ── Stream scoring for 10th graders ───────────────────────────────────────────

# Streams a 10th grader can actually choose in 12th grade (India education system)
# College/degree-level streams are excluded — those come after 12th
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
        s.stream_code: s
        for s in Stream.objects.filter(
            is_active=True, deleted=False, stream_code__in=_VALID_12TH_STREAMS
        )
    }
    stream_scores: dict[str, float] = {}
    for dim, codes in _DIM_STREAM_AFFINITY.items():
        dim_val = dim_scores.get(dim, 0.0)
        for code in codes:
            if code in _VALID_12TH_STREAMS:
                stream_scores[code] = stream_scores.get(code, 0.0) + dim_val

    # Ensure all valid streams appear even if score is 0
    for code in _VALID_12TH_STREAMS:
        if code not in stream_scores:
            stream_scores[code] = 0.0

    top_dim = max(DIMENSIONS, key=lambda d: dim_scores.get(d, 0.0))
    results = []
    for code, score in sorted(stream_scores.items(), key=lambda x: -x[1]):
        s = all_streams.get(code)
        if not s:
            continue
        results.append(
            {
                "stream_code": code,
                "stream_name": s.stream_name,
                "score": round(score, 2),
                "description": getattr(s, "description", "") or "",
                "traditional_equivalent": getattr(s, "traditional_equivalent", "")
                or "",
                "reason": f"Suits your {top_dim} strength",
            }
        )
    return results[:6]


def _score_domains_from_stream_codes(
    *, stream_codes: list[str], dim_scores: dict[str, float]
) -> tuple[list[dict], dict, set]:
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
    for m in rows:
        did = m.domain_id
        w = int(getattr(m, "weight_score", 0) or 0)
        if w > best_stream_weight_by_domain.get(did, 0):
            best_stream_weight_by_domain[did] = w
            domain_ref[did] = m.domain

    items: list[dict] = []
    top_pk_by_id: dict[str, Any] = {}
    score_by_id: dict[Any, float] = {}
    for did, stream_w in best_stream_weight_by_domain.items():
        d = domain_ref[did]
        domain_code = getattr(d, "domain_code", "") or ""
        affinity = _domain_affinity_from_domain(d)
        final = _domain_fit_score(affinity=affinity, dim_scores=dim_scores, stream_weight=stream_w)
        score_by_id[did] = float(final)

        affinity_for_reason = affinity or {dim: 0.25 for dim in DIMENSIONS}
        top_dim = max(affinity_for_reason, key=lambda k: dim_scores.get(k, 0.0) * affinity_for_reason.get(k, 0.0))
        dim_label = {"interest": "interest", "aptitude": "aptitude", "personality": "personality fit", "work_style": "work style"}.get(top_dim, top_dim)
        reason = f"Strong {dim_label} match for future stream options"
        items.append(
            {
                "id": str(did),
                "name": getattr(d, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": reason.capitalize(),
            }
        )
        top_pk_by_id[str(did)] = did

    items.sort(key=lambda x: (-x["score"], x["name"]))
    top = items[:10]
    top_domain_pk_set = {top_pk_by_id[x["id"]] for x in top if x["id"] in top_pk_by_id}
    return top, score_by_id, top_domain_pk_set


# ── Domain scoring (shared across tiers) ──────────────────────────────────────

def _domain_fit_score(*, affinity: dict[str, float] | None, dim_scores: dict[str, float], stream_weight: int) -> float:
    """
    Score = 70% from how well user's dimension scores match domain's affinity profile
            30% from stream-domain mapping weight (relevance of stream to domain)
    This ensures diverse results — a creative user gets creative domains regardless of stream.
    """
    if affinity:
        fit = sum(dim_scores.get(d, 0.0) * w for d, w in affinity.items())
    else:
        # fallback for domains not in affinity map: use equal weights
        fit = sum(dim_scores.get(d, 0.0) for d in DIMENSIONS) / len(DIMENSIONS)
    # Normalise stream weight to 0-100 scale and blend
    return (fit * 0.70) + (stream_weight * 0.30)


def _score_domains(
    *, ctx: _UserContext, dim_scores: dict[str, float]
) -> tuple[list[dict], dict, set]:
    rows = list(
        StreamDomainMapping.objects.filter(
            stream_id=ctx.stream_id, deleted=False, is_active=True,
            domain__deleted=False, domain__is_active=True,
        ).select_related("domain")
        .only("id", "weight_score", "domain__id", "domain__domain_name",
              "domain__domain_code", "domain__future_relevance_score",
              "domain__interest_weight", "domain__aptitude_weight", "domain__personality_weight", "domain__work_style_weight")
    )
    if not rows:
        return [], {}, set()

    items: list[dict] = []
    score_by_id: dict[Any, float] = {}

    for m in rows:
        d = m.domain
        stream_w = int(getattr(m, "weight_score", 0) or 0)
        affinity = _domain_affinity_from_domain(d)
        final = _domain_fit_score(affinity=affinity, dim_scores=dim_scores, stream_weight=stream_w)
        score_by_id[d.pk] = float(final)

        # Build human-readable reason from top contributing dimension for this domain
        affinity_for_reason = affinity or {d: 0.25 for d in DIMENSIONS}
        top_dim = max(affinity_for_reason, key=lambda k: dim_scores.get(k, 0.0) * affinity_for_reason.get(k, 0.0))
        dim_label = {"interest": "interest", "aptitude": "aptitude",
                     "personality": "personality fit", "work_style": "work style"}.get(top_dim, top_dim)
        rel = getattr(d, "future_relevance_score", None)
        rel_note = (
            " · high future relevance"
            if rel and rel >= 80
            else " · niche future relevance" if rel and rel <= 40 else ""
        )
        reason = f"Strong {dim_label} match{rel_note}".capitalize()

        items.append(
            {
                "id": str(d.pk),
                "name": getattr(d, "domain_name", "") or "",
                "score": round(float(final), 2),
                "reason": reason,
            }
        )

    items.sort(key=lambda x: (-x["score"], x["name"]))
    top = items[:10]
    # Build pk_set from the actual top items — not from stream rows (avoids mismatch after re-sort)
    top_id_set = {x["id"] for x in top}
    pk_set = {m.domain.pk for m in rows if str(m.domain.pk) in top_id_set}
    return top, score_by_id, pk_set


# ── Career scoring ─────────────────────────────────────────────────────────────


def _score_careers(
    *,
    top_domain_pk_set: set,
    domain_score_by_id: dict,
    top_dim: str,
    edu_seq: int,
    filter_by_edu: bool,
) -> list[dict]:
    dim_label = {
        "interest": "interest",
        "aptitude": "aptitude",
        "personality": "personality",
        "work_style": "work style",
    }.get(top_dim, top_dim)

    career_filter: dict[str, Any] = dict(
        domain_id__in=top_domain_pk_set,
        deleted=False,
        is_active=True,
        domain__deleted=False,
        domain__is_active=True,
        career__deleted=False,
        career__is_active=True,
    )
    if filter_by_edu:
        career_filter["career__min_education_level__sequence_order__lte"] = edu_seq

    rows = list(
        DomainCareerMapping.objects.filter(**career_filter)
        .select_related("domain", "career", "career__min_education_level")
        .order_by("-weight_score", "career__career_name")
    )

    career_map: dict[str, dict] = {}
    for m in rows:
        dscore = float(domain_score_by_id.get(m.domain_id, 0.0))
        mw = int(getattr(m, "weight_score", 0) or 0)
        cscore = (dscore * mw) / 100.0
        align = "strong" if mw >= 80 else ("good" if mw >= 60 else "moderate")
        entry = {
            "id": str(m.career_id),
            "name": getattr(m.career, "career_name", "") or "",
            "score": round(cscore, 2),
            "reason": f"From {getattr(m.domain, 'domain_name', '') or 'your top domain'}: {align} fit driven by your {dim_label}",
        }
        cid = entry["id"]
        if cid not in career_map or cscore > career_map[cid]["score"]:
            career_map[cid] = entry

    result = sorted(career_map.values(), key=lambda x: (-x["score"], x["name"]))
    return result[:20]


# ── Skill gap scoring ──────────────────────────────────────────────────────────


def _score_skill_gaps(
    *, top_domain_pk_set: set, user_id: int, dim_scores: dict[str, float]
) -> list[dict]:
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
    req: dict[Any, int] = {}
    names: dict[Any, str] = {}
    for m in skill_rows:
        sid = m.skill_id
        w = int(getattr(m, "weight_score", 0) or 0)
        if w > req.get(sid, 0):
            req[sid] = w
        names[sid] = getattr(m.skill, "skill_name", "") or ""

    user_skills = {
        r.skill_id: int(r.proficiency_score)
        for r in UserSkill.objects.filter(
            user_id=user_id,
            deleted=False,
            is_active=True,
            skill__deleted=False,
            skill__is_active=True,
        ).only("skill_id", "proficiency_score")
    }

    rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    gaps = []
    for sid, rw in req.items():
        prof = user_skills.get(sid) or _estimate_proficiency(
            skill_name=names.get(sid, ""), dim_scores=dim_scores
        )
        level = _gap_level(rw - prof)
        gaps.append({"skill": names.get(sid, ""), "gap_level": level})

    gaps.sort(key=lambda x: (rank.get(x["gap_level"], 99), x["skill"]))
    return gaps[:50]


# ── Main entry point ───────────────────────────────────────────────────────────

def generate_recommendation(user_id: int, *, ctx_override: _UserContext | None = None) -> dict[str, Any]:
    User = get_user_model()
    if not User.objects.filter(pk=user_id).exists():
        return _empty("User not found.")

    ctx = ctx_override or _fetch_context(user_id=user_id)
    if ctx is None:
        return _empty(
            "Complete your profile (education level + stream) to get recommendations."
        )

    dim_scores = _assessment_dimension_scores(user_id=user_id)
    top_dim, _ = _top_factor(dim_scores)
    seq = ctx.education_sequence

    # ── TIER 1: 10th grade ────────────────────────────────────────────────────
    if seq <= TIER_10TH:
        recommended_streams = _recommend_streams(dim_scores=dim_scores)
        stream_codes = [
            s.get("stream_code") for s in recommended_streams if s.get("stream_code")
        ]
        top_domains, domain_score_by_id, top_domain_pk_set = (
            _score_domains_from_stream_codes(
                stream_codes=stream_codes,
                dim_scores=dim_scores,
            )
        )
        top_careers = (
            _score_careers(
                top_domain_pk_set=top_domain_pk_set,
                domain_score_by_id=domain_score_by_id,
                top_dim=top_dim,
                edu_seq=seq,
                filter_by_edu=False,
            )
            if top_domain_pk_set
            else []
        )
        skill_gaps = (
            _score_skill_gaps(
                top_domain_pk_set=top_domain_pk_set,
                user_id=user_id,
                dim_scores=dim_scores,
            )
            if top_domain_pk_set
            else []
        )
        # Keep only stronger signals for cleaner 10th-grade output.
        strong_top_careers = [
            c for c in top_careers if float(c.get("score", 0.0)) >= 40.0
        ]
        medium_high_skill_gaps = [
            g for g in skill_gaps if g.get("gap_level") in {"HIGH", "MEDIUM"}
        ]
        # Keep 10th-grade response concise but informative.
        recommended_streams = recommended_streams[:4]
        top_domains = top_domains[:6]
        top_careers = (strong_top_careers or top_careers)[:8]
        skill_gaps = (medium_high_skill_gaps or skill_gaps)[:10]
        return {
            "tier": "10th",
            "message": "Based on your assessment, here are the best streams to choose in 12th grade.",
            "recommended_streams": recommended_streams,
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": skill_gaps,
            "next_step": "Choose your 12th stream, then retake the assessment for domain and career recommendations.",
        }

    # ── TIER 2: 12th grade ────────────────────────────────────────────────────
    if seq == TIER_12TH:
        top_domains, _, _ = _score_domains(ctx=ctx, dim_scores=dim_scores)
        if not top_domains:
            return _empty("No domain mappings found for your stream.")
        return {
            "tier": "12th",
            "message": "Based on your stream and assessment, here are the best domains to pursue in college.",
            "recommended_streams": [],
            "top_domains": top_domains,
            "top_careers": [],
            "skill_gaps": [],
            "next_step": "Enroll in a relevant degree program. Complete your graduation to unlock career recommendations.",
        }

    # ── TIER 3: ITI / Diploma ─────────────────────────────────────────────────
    if seq <= TIER_DIPLOMA:
        top_domains, domain_score_by_id, top_domain_pk_set = _score_domains(
            ctx=ctx, dim_scores=dim_scores
        )
        if not top_domains:
            return _empty("No domain mappings found for your stream.")
        top_careers = _score_careers(
            top_domain_pk_set=top_domain_pk_set,
            domain_score_by_id=domain_score_by_id,
            top_dim=top_dim,
            edu_seq=seq,
            filter_by_edu=True,
        )
        return {
            "tier": "diploma",
            "message": "Here are domains and entry-level careers suited to your profile.",
            "recommended_streams": [],
            "top_domains": top_domains,
            "top_careers": top_careers,
            "skill_gaps": [],
            "next_step": "Consider upgrading to a degree program to unlock more career options and skill gap analysis.",
        }

    # ── TIER 4: Graduate+ ─────────────────────────────────────────────────────
    top_domains, domain_score_by_id, top_domain_pk_set = _score_domains(
        ctx=ctx, dim_scores=dim_scores
    )
    if not top_domains:
        return _empty("No domain mappings found for your stream.")

    top_careers = _score_careers(
        top_domain_pk_set=top_domain_pk_set,
        domain_score_by_id=domain_score_by_id,
        top_dim=top_dim,
        edu_seq=seq,
        filter_by_edu=False,
    )
    skill_gaps = _score_skill_gaps(
        top_domain_pk_set=top_domain_pk_set, user_id=user_id, dim_scores=dim_scores
    )

    has_assessment = UserResponse.objects.filter(
        user_id=user_id, question__is_active=True
    ).exists()
    message = (
        "ok"
        if has_assessment
        else "Complete the assessment for more accurate recommendations."
    )

    return {
        "tier": "graduate",
        "message": message,
        "recommended_streams": [],
        "top_domains": top_domains,
        "top_careers": top_careers,
        "skill_gaps": skill_gaps,
        "next_step": None,
    }
