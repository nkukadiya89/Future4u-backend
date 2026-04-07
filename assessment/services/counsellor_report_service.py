"""
Counsellor Report Service
Builds student-facing recommendation reports from engine output.
All content (why, notes, next steps) is DB-driven via DomainReportMeta / StreamReportMeta.
"""

from __future__ import annotations


# ── DB accessors ──────────────────────────────────────────────────────────────


def _get_domain_meta(domain_code: str) -> dict:
    try:
        from domain.models import DomainReportMeta

        obj = DomainReportMeta.objects.filter(domain_code=domain_code).first()
        if obj and obj.degrees:
            return {
                "degrees": obj.degrees_list(),
                "careers": obj.careers_list(),
                "note": obj.note,
                "how_to_choose_hint": obj.how_to_choose_hint,
                "next_steps": obj.next_steps(),
            }
    except Exception:
        pass
    return {
        "degrees": ["Bachelor's degree in a relevant field"],
        "careers": ["Analyst", "Specialist", "Consultant"],
        "note": "Check what this field covers day-to-day before committing.",
        "how_to_choose_hint": "",
        "next_steps": [],
    }


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
    return {
        "why": "This stream is the closest match based on your responses.",
        "subjects": ["Core subjects for this stream"],
        "careers": ["Relevant careers"],
        "note": "Look at what this stream covers in 11th before deciding.",
        "next_steps": [
            "Look at the actual subjects this stream covers in 11th before deciding",
            "Talk to someone already in this stream about what the workload is like",
            "Pick based on what you will enjoy studying for 2 years, not what sounds impressive",
        ],
    }


# ── Direction why (DB-first, inline fallback for unknown codes) ───────────────

_DIRECTION_WHY = {
    "ai_data": "This field is about building systems that find patterns in data and turn them into decisions or predictions.",
    "cloud_computing": "The work is about keeping large-scale systems running — infrastructure, reliability, and scale.",
    "cybersecurity": "The job is finding weaknesses before attackers do, and building defenses that hold.",
    "devops": "The work sits between writing software and keeping it running reliably in production.",
    "fintech": "The work combines financial systems with software — payments, lending, trading, and risk.",
    "healthtech": "The job is using technology to improve how healthcare is delivered and managed.",
    "biotech": "The work involves biological research — lab-based, long-cycle, and science-heavy.",
    "robotics": "The job is designing and building machines that move, sense, and respond to the physical world.",
    "manufacturing": "The work is about designing and optimising physical production processes.",
    "digital_marketing": "The job is driving measurable growth for businesses through online channels.",
    "creator_economy": "The work is producing content — video, writing, audio — and building an audience around it.",
    "entrepreneurship": "The work is building a business from scratch — product, customers, and operations.",
    "renewable_energy": "The job is designing and deploying clean energy systems — solar, wind, and storage.",
    "ev_mobility": "The work is engineering the systems that power electric vehicles — batteries, motors, and software.",
    "iot": "The job is connecting physical devices to software systems and making them work together.",
    "legaltech": "The work applies technology to legal processes — contracts, compliance, and research.",
    "edtech": "The job is building tools and content that help people learn more effectively.",
    "pharma": "The work involves drug development, testing, and getting medicines to market.",
    "nanotech": "The job is working with materials and systems at the nanoscale — mostly research-stage.",
    "sports_tech": "The work applies science and data to improve athletic performance and health outcomes.",
    "hrtech": "The job is managing people, hiring, and building workplace systems — increasingly data-driven.",
    "ecommerce": "The work is running and growing online retail operations — logistics, marketing, and tech.",
    "agritech": "The job is applying technology to farming and food systems to improve yield and efficiency.",
    "climate_tech": "The work is building solutions to reduce emissions or help industries adapt to climate change.",
    "gaming": "The job is designing and building interactive games — code, art, and systems together.",
    "ar_vr": "The work is building immersive digital experiences for training, retail, or entertainment.",
    "blockchain": "The job is building decentralised systems — smart contracts, protocols, and Web3 products.",
    "data_engineering": "The work is building pipelines and infrastructure that make data usable at scale.",
    "supply_chain": "The job is managing how goods move from production to delivery — logistics and operations.",
    "mental_health": "The work involves supporting people through psychological difficulty — clinical or research.",
    "defense_tech": "The job is developing technology for national security — systems, intelligence, and defense.",
    "space_tech": "The work is engineering systems for space — satellites, launch vehicles, and mission operations.",
}


def _direction_why(domain_name: str, confidence: int, domain_code: str) -> str:
    if confidence >= 55:
        return _DIRECTION_WHY.get(
            domain_code, f"{domain_name} is a strong fit based on your responses."
        )
    return f"{domain_name} is the closest match so far. Answer a few more questions to sharpen this."


# ── How-to-choose ─────────────────────────────────────────────────────────────


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


# ── Level-based next step fallbacks (used when DB has no domain-specific steps) ──

_LEVEL_NEXT_STEPS = {
    "higher_secondary": [
        "Check the first-year subjects for your top degree option at 2-3 colleges you are considering",
        "Try one small real thing in this field before you commit",
        "Talk to one person already studying or working in this field",
    ],
    "iti": [
        "Find a short apprenticeship or hands-on project in your top field before committing",
        "Look at which certifications are actually valued by employers in your trade",
        "Talk to someone working in this field about what skills get people hired",
    ],
    "diploma": [
        "Look into lateral entry B.Tech options if you want to go further academically",
        "Find an internship or project in your top domain to start building a portfolio",
        "Get one industry-recognised certification relevant to your area",
    ],
    "graduation": [
        "Get one internship or project in your top domain — real exposure will sharpen your direction fast",
        "Check actual job postings in this field to see what skills companies ask for",
        "Decide whether a PG degree adds value for the specific role you are targeting",
    ],
    "post_graduation": [
        "Find someone 5 years ahead of you in this field and ask what they wish they had specialised in earlier",
        "Compare research vs. industry roles in your field — the day-to-day is very different",
        "Build one portfolio piece that clearly demonstrates your specialisation",
    ],
    "doctorate": [
        "Identify 2-3 research groups working on problems you find genuinely interesting",
        "Look at industry research roles alongside academia — the boundary is blurring fast",
        "Connect with a postdoc or early-career researcher in your area",
    ],
    "professional": [
        "Look at what skills are opening doors for people 2-3 levels above you in this field",
        "Decide whether a lateral move or deeper specialisation makes more sense right now",
        "Find someone who has made the transition you are considering and ask them directly",
    ],
}

_DEFAULT_NEXT_STEPS = [
    "Check the first-year subjects for your top option before deciding",
    "Try one small real thing in this field to see if it holds your interest",
    "Talk to one person already studying or working in this field",
]


# ── Stream report (10th grade) ────────────────────────────────────────────────


def _build_stream_report(recommendation: dict) -> dict | None:
    stream_ranking = recommendation.get("stream_ranking") or []
    if not stream_ranking:
        return None

    top = stream_ranking[0]
    top_code = top.get("stream_code", "")
    top_name = top.get("stream_name", top_code)
    top_db = _get_stream_meta(top_code)

    direction = {"name": top_name, "why": top_db["why"]}

    top_options = []
    for entry in stream_ranking[:3]:
        code = entry.get("stream_code", "")
        name = entry.get("stream_name", code)
        meta = _get_stream_meta(code)
        top_options.append(
            {
                "name": name,
                "subjects": meta["subjects"],
                "careers": meta["careers"],
                "note": meta["note"],
            }
        )

    if len(top_options) >= 3:
        a, b, c = top_options[0]["name"], top_options[1]["name"], top_options[2]["name"]
        ha = _get_stream_meta(stream_ranking[0].get("stream_code", "")).get(
            "how_to_choose_hint", ""
        )
        hb = _get_stream_meta(stream_ranking[1].get("stream_code", "")).get(
            "how_to_choose_hint", ""
        )
        hc = _get_stream_meta(stream_ranking[2].get("stream_code", "")).get(
            "how_to_choose_hint", ""
        )
        if ha and hb and hc:
            how_to_choose = f"Go with {a} if {ha.rstrip('.')}. Pick {b} if {hb.rstrip('.')}. Choose {c} if {hc.rstrip('.')}."
        else:
            how_to_choose = (
                f"Go with {a} — it came through most strongly in your answers. "
                f"{b} is the next closest fit. {c} is worth considering if neither feels right."
            )
    elif len(top_options) == 2:
        a, b = top_options[0]["name"], top_options[1]["name"]
        how_to_choose = f"Go with {a} if it matches what you genuinely enjoy studying. Pick {b} if {a} feels like a stretch."
    else:
        how_to_choose = f"Go with {top_options[0]['name']} — it is the clearest fit."

    return {
        "direction": direction,
        "top_options": top_options,
        "how_to_choose": how_to_choose,
        "next_steps": top_db["next_steps"],
    }


# ── Domain report (12th and above) ───────────────────────────────────────────


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

    direction = {
        "name": top_name,
        "why": _direction_why(top_name, confidence, top_code),
    }

    top_options = []
    for entry in domain_ranking[:3]:
        code = entry.get("domain_code", "")
        name = entry.get("domain_name", code)
        meta = _get_domain_meta(code)
        top_options.append(
            {
                "name": name,
                "degrees": meta["degrees"],
                "careers": meta["careers"],
                "note": meta["note"],
                "how_to_choose_hint": meta["how_to_choose_hint"],
            }
        )

    how_to_choose = _how_to_choose(top_options)
    for opt in top_options:
        opt.pop("how_to_choose_hint", None)

    top_meta = _get_domain_meta(top_code)
    # Use level-appropriate next steps — domain meta steps are degree-focused
    # so only use them for 12th/graduation levels; fall back to level steps otherwise
    degree_levels = {"higher_secondary", "graduation"}
    if education_level in degree_levels and top_meta.get("next_steps"):
        next_steps = top_meta["next_steps"]
    else:
        next_steps = _LEVEL_NEXT_STEPS.get(education_level, _DEFAULT_NEXT_STEPS)

    return {
        "direction": direction,
        "top_options": top_options,
        "how_to_choose": how_to_choose,
        "next_steps": next_steps,
    }
