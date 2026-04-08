"""
Counsellor Report Service — fully DB-driven.
Content comes from DomainReportMeta, StreamReportMeta, and EducationLevel.
"""
from __future__ import annotations


def _get_domain_meta(domain_code: str) -> dict:
    try:
        from domain.models import DomainReportMeta
        obj = DomainReportMeta.objects.filter(domain_code=domain_code).first()
        if obj and obj.degrees:
            return {
                "degrees": obj.degrees_list(),
                "careers": obj.careers_list(),
                "note": obj.note,
                "direction_why": obj.direction_why if hasattr(obj, "direction_why") else "",
                "how_to_choose_hint": obj.how_to_choose_hint,
                "next_steps": obj.next_steps(),
            }
    except Exception:
        pass
    return {"degrees": [], "careers": [], "note": "", "direction_why": "", "how_to_choose_hint": "", "next_steps": []}


def _get_stream_meta(stream_code: str) -> dict:
    try:
        from domain.models import StreamReportMeta
        obj = StreamReportMeta.objects.filter(stream_code=stream_code).first()
        if obj and obj.why:
            return {
                "why": obj.why,
                "subjects": obj.subjects_list(),
                "careers": obj.careers_list(),
                "note": obj.note,
                "next_steps": obj.next_steps(),
            }
    except Exception:
        pass
    return {"why": "", "subjects": [], "careers": [], "note": "", "next_steps": []}


def _get_level_next_steps(level_code: str) -> list[str]:
    try:
        from education_level.models import EducationLevel
        obj = EducationLevel.objects.filter(
            level_code=level_code, is_active=True, deleted=False
        ).only("next_step_1", "next_step_2", "next_step_3").first()
        if obj:
            return [s for s in [obj.next_step_1, obj.next_step_2, obj.next_step_3] if s.strip()]
    except Exception:
        pass
    return []


def _direction_why(domain_name: str, confidence: int, domain_code: str) -> str:
    try:
        from domain.models import DomainReportMeta
        obj = DomainReportMeta.objects.filter(domain_code=domain_code).only("direction_why").first()
        if obj and hasattr(obj, "direction_why") and obj.direction_why:
            if confidence >= 55:
                return obj.direction_why
            return f"{domain_name} is the closest match so far. Answer a few more questions to sharpen this."
    except Exception:
        pass
    if confidence >= 55:
        return f"{domain_name} is a strong fit based on your responses."
    return f"{domain_name} is the closest match so far. Answer a few more questions to sharpen this."


def _how_to_choose(top_options: list[dict]) -> str:
    if len(top_options) == 1:
        return f"Go with {top_options[0]['name']}. Look at what the degree actually covers day-to-day before you commit."

    hints = [o.get("how_to_choose_hint", "") for o in top_options]

    if len(top_options) == 2:
        a, b = top_options[0]["name"], top_options[1]["name"]
        ha, hb = hints[0], hints[1]
        if ha and hb:
            return f"Choose {a} if {ha.rstrip('.')}. Choose {b} if {hb.rstrip('.')}."
        return f"Go with {a} — it is the stronger fit. If something about it does not work for you, {b} is the next best option."

    a, b, c = top_options[0]["name"], top_options[1]["name"], top_options[2]["name"]
    ha, hb, hc = hints[0], hints[1], hints[2]
    parts = []
    if ha:
        parts.append(f"Choose {a} if {ha.rstrip('.')}.")
    if hb:
        parts.append(f"Choose {b} if {hb.rstrip('.')}.")
    if hc:
        parts.append(f"Choose {c} if {hc.rstrip('.')}.")
    if parts:
        return " ".join(parts)
    return f"Go with {a} first. If it does not feel right, {b} is the next closest fit. {c} is worth considering if you want a different direction."


def _build_stream_report(recommendation: dict) -> dict | None:
    stream_ranking = recommendation.get("stream_ranking") or []
    if not stream_ranking:
        return None

    top = stream_ranking[0]
    top_code = top.get("stream_code", "")
    top_name = top.get("stream_name", top_code)
    top_db = _get_stream_meta(top_code)

    top_options = []
    for entry in stream_ranking[:3]:
        code = entry.get("stream_code", "")
        name = entry.get("stream_name", code)
        meta = _get_stream_meta(code)
        top_options.append({"name": name, "subjects": meta["subjects"], "careers": meta["careers"], "note": meta["note"]})

    if len(top_options) >= 3:
        a, b, c = top_options[0]["name"], top_options[1]["name"], top_options[2]["name"]
        ha = _get_stream_meta(stream_ranking[0].get("stream_code", "")).get("how_to_choose_hint", "")
        hb = _get_stream_meta(stream_ranking[1].get("stream_code", "")).get("how_to_choose_hint", "")
        hc = _get_stream_meta(stream_ranking[2].get("stream_code", "")).get("how_to_choose_hint", "")
        if ha and hb and hc:
            how_to_choose = f"Go with {a} if {ha.rstrip('.')}. Pick {b} if {hb.rstrip('.')}. Choose {c} if {hc.rstrip('.')}."
        else:
            how_to_choose = f"Go with {a} — it came through most strongly in your answers. {b} is the next closest fit. {c} is worth considering if neither feels right."
    elif len(top_options) == 2:
        a, b = top_options[0]["name"], top_options[1]["name"]
        how_to_choose = f"Go with {a} if it matches what you genuinely enjoy studying. Pick {b} if {a} feels like a stretch."
    else:
        how_to_choose = f"Go with {top_options[0]['name']} — it is the clearest fit."

    return {
        "direction": {"name": top_name, "why": top_db["why"]},
        "top_options": top_options,
        "how_to_choose": how_to_choose,
        "next_steps": top_db["next_steps"],
    }


def build_counsellor_report(recommendation: dict) -> dict | None:
    rec_type = recommendation.get("recommendation_type")
    confidence = recommendation.get("confidence", 0)
    education_level = recommendation.get("education_level")

    if not rec_type or confidence == 0:
        return None

    if rec_type == "stream":
        return _build_stream_report(recommendation)

    domain_ranking = recommendation.get("domain_ranking") or []
    if not domain_ranking:
        return None

    top = domain_ranking[0]
    top_code = top.get("domain_code", "")
    top_name = top.get("domain_name", top_code)

    top_options = []
    for entry in domain_ranking[:3]:
        code = entry.get("domain_code", "")
        name = entry.get("domain_name", code)
        meta = _get_domain_meta(code)
        top_options.append({
            "name": name,
            "degrees": meta["degrees"],
            "careers": meta["careers"],
            "note": meta["note"],
            "how_to_choose_hint": meta["how_to_choose_hint"],
        })

    how_to_choose = _how_to_choose(top_options)
    for opt in top_options:
        opt.pop("how_to_choose_hint", None)

    top_meta = _get_domain_meta(top_code)
    degree_levels = {"higher_secondary", "graduation"}
    if education_level in degree_levels and top_meta.get("next_steps"):
        next_steps = top_meta["next_steps"]
    else:
        next_steps = _get_level_next_steps(education_level or "")

    return {
        "direction": {"name": top_name, "why": _direction_why(top_name, confidence, top_code)},
        "top_options": top_options,
        "how_to_choose": how_to_choose,
        "next_steps": next_steps,
    }
