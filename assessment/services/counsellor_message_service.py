"""
Counsellor messages — DB-driven. All content comes from DomainCounsellorKnowledge
and StreamCounsellorKnowledge. Hardcoded dicts are removed.
"""
from __future__ import annotations

# ── Confidence label thresholds ───────────────────────────────────────────────
# These define the UX copy shown to users based on their confidence score (0-100).
# Adjust here if the scoring formula changes.
CONFIDENCE_STRONG = 72       # "Strong match"
CONFIDENCE_GOOD = 55         # "Good match" — also used as the strong/weak branch point
CONFIDENCE_MODERATE = 38     # "Moderate match"
CONFIDENCE_EARLY = 20        # "Early signal"

# Tie threshold: two stream/domain scores within this many points are considered tied
SCORE_TIE_MARGIN = 5


def _clean(code: str) -> str:
    return code.split("__", 1)[-1].lower() if "__" in code else code.lower()


def _domain_display(code: str) -> str:
    clean = _clean(code)
    try:
        from domain.models import Domain
        obj = Domain.objects.filter(domain_code=clean, deleted=False).only("domain_name").first()
        if obj and obj.domain_name:
            return obj.domain_name
    except Exception:
        pass
    return clean.replace("_", " ").title()


def _stream_display(code: str) -> str:
    clean = _clean(code)
    try:
        from stream.models import Stream
        obj = Stream.objects.filter(stream_code=clean, deleted=False).only("stream_name").first()
        if obj and obj.stream_name:
            return obj.stream_name
    except Exception:
        pass
    return clean.replace("_", " ").title()


def _career_display(code: str) -> str:
    clean = _clean(code)
    try:
        from career.models import Career
        obj = Career.objects.filter(career_code=clean, deleted=False).only("career_name").first()
        if obj and obj.career_name:
            return obj.career_name
    except Exception:
        pass
    return clean.replace("_", " ").title()


def _dk(code: str) -> tuple:
    """Load domain counsellor knowledge from DB. Falls back to __default__ record."""
    clean = _clean(code)
    try:
        from domain.models import DomainCounsellorKnowledge
        obj = (
            DomainCounsellorKnowledge.objects.filter(domain_code=clean).first()
            or DomainCounsellorKnowledge.objects.filter(domain_code="__default__").first()
        )
        if obj and obj.insight:
            return obj.as_tuple()
    except Exception:
        pass
    return ("", "", "", "")


def _sk(code: str) -> tuple:
    """Load stream counsellor knowledge from DB. Falls back to __default__ record."""
    clean = _clean(code)
    try:
        from domain.models import StreamCounsellorKnowledge
        obj = (
            StreamCounsellorKnowledge.objects.filter(stream_code=clean).first()
            or StreamCounsellorKnowledge.objects.filter(stream_code="__default__").first()
        )
        if obj and obj.insight:
            return obj.as_tuple()
    except Exception:
        pass
    return ("", "", "", "")


def _confidence_label(confidence: int) -> str:
    if confidence >= CONFIDENCE_STRONG: return "Strong match"
    if confidence >= CONFIDENCE_GOOD: return "Good match"
    if confidence >= CONFIDENCE_MODERATE: return "Moderate match"
    if confidence >= CONFIDENCE_EARLY: return "Early signal"
    return "Not enough data yet"


def _get_level_fallback(level_code: str) -> tuple[str, str]:
    """Load fallback insight/action from EducationLevel DB record."""
    try:
        from education_level.models import EducationLevel
        obj = EducationLevel.objects.filter(
            level_code=level_code, is_active=True, deleted=False
        ).only("fallback_insight", "fallback_action").first()
        if obj and obj.fallback_insight:
            return (obj.fallback_insight, obj.fallback_action or "")
    except Exception:
        pass
    return _LEVEL_FALLBACK.get(level_code, (
        "We need a few more answers before we can give you something useful.",
        "Finish the assessment and we'll give you a personalised career direction.",
    ))


def build_counsellor_message(
    *,
    level_code: str | None,
    recommendation_type: str | None,
    top_stream: str | None = None,
    stream_ranking: list | None = None,
    top_domain: str | None = None,
    domain_ranking: list | None = None,
    top_career: str | None = None,
    career_scores: dict | None = None,
    confidence: int = 0,
    is_entry_level: bool = False,
    override_reason: str | None = None,
) -> dict:
    stream_ranking = stream_ranking or []
    domain_ranking = domain_ranking or []
    career_scores = career_scores or {}
    confidence_label = _confidence_label(confidence)
    strong = confidence >= CONFIDENCE_GOOD

    if not recommendation_type or confidence == 0:
        return _no_data_message(level_code)

    # ── 10th grade — stream ──────────────────────────────────────────────────
    if recommendation_type == "stream":
        code = top_stream or (stream_ranking[0].get("stream_code") if stream_ranking else None)
        if not code:
            return _no_data_message(level_code)
        k = _sk(code)
        stream_label = _stream_display(code)
        top_score = stream_ranking[0].get("score", 0) if stream_ranking else 0
        second = stream_ranking[1] if len(stream_ranking) > 1 else None
        tied = second and abs(top_score - second.get("score", 0)) <= SCORE_TIE_MARGIN
        second_label = _stream_display(second.get("stream_code", "")) if second else None

        if tied and second_label:
            insight = (
                f"Your responses split almost evenly between {stream_label} and {second_label}. "
                f"That's not a problem — it means you have real interest in both, which gives you flexibility. "
                f"{k[0]}"
            )
            action = (
                f"Spend a week looking at what each stream actually covers in 11th — "
                f"not the career outcomes, the subjects themselves. That usually makes the choice obvious."
            )
            tension = f"The real call: go deeper into {stream_label}, or keep your options open with {second_label}?"
        elif strong:
            insight = k[0]
            action = k[2]
            tension = k[3]
        else:
            insight = (
                f"There's a lean toward {stream_label} in your answers, but it's not a strong signal yet. "
                f"That's normal — most people at 10th grade haven't had enough exposure to be sure."
            )
            action = f"Don't pick based on what sounds impressive or what your friends are choosing. {k[2]}"
            tension = k[3]

        return {
            "label": f"Looks like {stream_label} is your direction",
            "confidence_label": confidence_label,
            "insight": insight,
            "tradeoff": k[1],
            "action": action,
            "tension": tension,
        }

    # ── 12th grade — college domain ──────────────────────────────────────────
    if recommendation_type == "college_domain":
        code = top_domain or (domain_ranking[0].get("domain_code") if domain_ranking else None)
        if not code:
            return _no_data_message(level_code)
        k = _dk(code)
        domain_label = _domain_display(code)
        second = domain_ranking[1] if len(domain_ranking) > 1 else None
        second_label = second.get("domain_name") if second else None

        if strong:
            insight = f"Across your answers, {domain_label} came through most consistently. {k[0]}"
            action = k[2]
        else:
            insight = (
                f"Your answers lean toward {domain_label}"
                + (f", with {second_label} close behind" if second_label else "")
                + f". The signal is moderate — at 12th grade that usually means not enough real exposure yet, not a wrong fit."
            )
            action = f"Before picking a degree, do this: {k[2].rstrip('.').lower()}. Real exposure will sharpen this fast."

        return {
            "label": f"{domain_label} looks like your field",
            "confidence_label": confidence_label,
            "insight": insight,
            "tradeoff": k[1],
            "action": action,
            "tension": k[3],
        }

    # ── Career recommendation ────────────────────────────────────────────────
    if recommendation_type == "career" and top_domain:
        k = _dk(top_domain)
        domain_label = _domain_display(top_domain)
        career_label = _career_display(top_career) if top_career else None
        second = domain_ranking[1] if len(domain_ranking) > 1 else None
        second_label = second.get("domain_name") if second else None
        override_note = ""

        label = f"You seem built for {career_label}" if career_label else f"{domain_label} looks like your space"

        if level_code in ("iti", "diploma"):
            if strong:
                insight = (
                    f"{domain_label} came through clearly in your answers{override_note}. "
                    f"At this level, a certification and hands-on experience will open more doors than a degree. {k[0]}"
                )
                action = f"Start here: {k[2]}"
                tension = k[3]
            else:
                insight = (
                    f"There's a lean toward {domain_label} in your answers"
                    + (f", though {second_label} also shows up" if second_label else "")
                    + f"{override_note}. The signal is still forming — try something practical before committing."
                )
                action = f"Find a short project or apprenticeship in {domain_label} first. Hands-on time will tell you more than any assessment."
                tension = f"The real call: go deeper in {domain_label} now, or explore {second_label} first?" if second_label else k[3]

        elif level_code in ("post_graduation", "doctorate", "professional"):
            if strong:
                insight = (
                    f"{domain_label} is where your answers land most consistently"
                    + (f" — {career_label} is the clearest role fit" if career_label else "")
                    + f"{override_note}. At this level, going deep beats staying broad. {k[0]}"
                )
                action = k[2]
                tension = k[3]
            else:
                insight = (
                    f"Your answers point toward {domain_label}"
                    + (f", with {second_label} also showing up" if second_label else "")
                    + f"{override_note}. A moderate signal at this level usually means you're between specialisations — worth resolving before your next move."
                )
                action = f"Find someone 5 years ahead of you in {domain_label} and ask what they wish they'd specialised in earlier."
                tension = k[3]

        else:  # graduation
            if strong:
                insight = (
                    f"{domain_label} came through most consistently across your answers"
                    + (f", pointing to {career_label} as the best-fit role" if career_label else "")
                    + f"{override_note}. {k[0]}"
                )
                action = k[2]
                tension = k[3]
            else:
                insight = (
                    f"Your answers show interest in {domain_label}"
                    + (f", though {second_label} is close" if second_label else "")
                    + f"{override_note}. A moderate signal at graduation level usually means not enough real exposure yet — not a wrong fit."
                )
                action = f"One internship or project in {domain_label} will sharpen this signal fast."
                tension = f"The real question: commit to {domain_label} now, or explore {second_label} first to be sure?" if second_label else k[3]

        return {
            "label": label,
            "confidence_label": confidence_label,
            "insight": insight,
            "tradeoff": k[1],
            "action": action,
            "tension": tension,
        }

    return _no_data_message(level_code)


# ── Level-aware no-data fallback ─────────────────────────────────────────────
# These are last-resort safety nets only — primary content comes from EducationLevel DB records.

_LEVEL_FALLBACK = {
    "secondary": (
        "You haven't answered enough questions yet — we need a bit more to go on before pointing you toward a stream.",
        "Keep going with the assessment. The more you answer, the more accurately we can match you to the right path for 11th and 12th.",
    ),
    "higher_secondary": (
        "We don't have enough from you yet to suggest a college direction with any confidence.",
        "Finish the assessment and we'll be able to tell you which field actually fits your strengths and interests.",
    ),
    "iti": (
        "Your responses are a bit sparse right now — not enough to make a call we'd stand behind.",
        "Answer the remaining questions and we'll match you to the right trade or technical path.",
    ),
    "diploma": (
        "We're not there yet — a few more answers and we'll have something useful for you.",
        "Finish the assessment and we'll give you a career direction that fits your diploma specialisation.",
    ),
    "graduation": (
        "We need a bit more from you before we can point you toward a career that actually fits.",
        "Try to answer at least 15 questions across different areas — that's usually enough for a solid result.",
    ),
    "post_graduation": (
        "Not enough to go on yet for a PG-level recommendation.",
        "Complete the assessment and we'll help you figure out the right specialisation for where you're headed.",
    ),
    "doctorate": (
        "We need more responses before we can suggest a research direction that makes sense for your profile.",
        "Finish the assessment and we'll give you something aligned with your doctoral background.",
    ),
    "professional": (
        "We don't have enough yet to make a recommendation that respects your experience level.",
        "Complete the full assessment and we'll give you a direction that actually fits where you are.",
    ),
}

_NO_PROFILE_FALLBACK = (
    "We don't know your education level yet, so we can't point you anywhere useful.",
    "Set your education level and stream in your profile first — that's what we use to filter and score everything.",
)


def _no_data_message(level_code: str | None) -> dict:
    if not level_code:
        insight, action = _NO_PROFILE_FALLBACK
    else:
        insight, action = _get_level_fallback(level_code)
    return {
        "label": "Let's get a bit more from you first",
        "confidence_label": "Not enough data yet",
        "insight": insight,
        "tradeoff": None,
        "action": action,
        "tension": None,
    }
