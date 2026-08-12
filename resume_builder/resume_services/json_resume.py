"""
Deterministic adapter between the Future4U resume dict and the canonical
JSON Resume schema. Pure Python — the LLM never produces this mapping.

Pipeline: Future4U profile data -> existing AI content -> protected merge
          -> to_json_resume() -> validated JSON Resume

Also provides resume_json_to_template_data() so stored resumes can be
re-rendered into the legacy Jinja templates WITHOUT another AI call.
"""

from __future__ import annotations

# The full JSON Resume skeleton. Every key is always present so themes and
# the validator see a stable contract (empty collections when no data exists).
JSON_RESUME_SECTIONS = [
    "basics",
    "work",
    "volunteer",
    "education",
    "awards",
    "certificates",
    "publications",
    "skills",
    "languages",
    "interests",
    "projects",
    "references",
]

# Deterministic skill group mapping (Future4U dict key -> JSON Resume group).
_SKILL_GROUPS = [
    ("technical", "Technical Skills"),
    ("soft", "Soft Skills"),
    ("tools", "Tools"),
    ("domain_knowledge", "Domain Knowledge"),
    ("leadership", "Leadership"),
]
_SKILL_GROUP_TO_KEY = {name.lower(): key for key, name in _SKILL_GROUPS}


# ---------------------------------------------------------------------------
# Forward adapter: Future4U dict -> JSON Resume
# ---------------------------------------------------------------------------
def to_json_resume(data: dict) -> dict:
    """Convert the merged Future4U resume dict into the canonical JSON Resume."""
    resume = {section: [] for section in JSON_RESUME_SECTIONS}
    resume["basics"] = _build_basics(data)
    resume["work"] = _build_work(data, resume)
    resume["education"] = _build_education(data)
    resume["skills"] = _build_skills(data)
    resume["projects"] += _build_projects(data)
    resume["certificates"] = _build_certificates(data)
    resume["awards"] = _build_awards(data)
    resume["interests"] = _build_interests(data)
    resume["languages"] = _build_languages(data)
    return resume


def _build_basics(data: dict) -> dict:
    pi = data.get("personal_info") or {}
    cd = data.get("career_direction") or {}
    cp = data.get("career_positioning") or {}

    label = (
        pi.get("designation")
        or cd.get("target_role")
        or cp.get("current_role")
        or cp.get("target_role")
        or ""
    )

    profiles = []
    for network, url in (
        ("LinkedIn", pi.get("linkedin")),
        ("GitHub", pi.get("github")),
        ("Portfolio", pi.get("portfolio")),
    ):
        if url:
            profiles.append({"network": network, "url": str(url)})

    location = {}
    if pi.get("city"):
        location["city"] = str(pi["city"])
    if pi.get("state"):
        location["region"] = str(pi["state"])
    if pi.get("country"):
        location["countryCode"] = str(pi["country"])
    if not location and pi.get("location"):
        location["city"] = str(pi["location"])

    return {
        "name": pi.get("name") or "",
        "label": label or "",
        "image": pi.get("profile_image") or "",
        "email": pi.get("email") or "",
        "phone": pi.get("phone") or "",
        "url": pi.get("portfolio") or "",
        "summary": data.get("summary") or pi.get("about_me") or "",
        "location": location,
        "profiles": profiles,
    }


def _parse_duration(duration):
    """Best-effort split of a duration string into (start, end). Never invents dates."""
    if not duration:
        return None, None
    parts = [p.strip() for p in str(duration).replace(" to ", " - ").split("-")]
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def _build_work(data: dict, resume: dict) -> list:
    work = []
    is_fresher = data.get("resume_type") != "professional"

    if is_fresher:
        for i in data.get("internships") or []:
            if not isinstance(i, dict):
                continue
            start, end = _parse_duration(i.get("duration"))
            item = {"company": i.get("company") or "", "position": "Intern"}
            if start:
                item["startDate"] = start
            if end:
                item["endDate"] = end
            highlights = [str(r) for r in (i.get("responsibilities") or [])]
            if highlights:
                item["highlights"] = highlights
            if i.get("key_achievement"):
                item["summary"] = str(i["key_achievement"])
            work.append(item)
    else:
        for e in data.get("experience") or []:
            if not isinstance(e, dict):
                continue
            start, end = _parse_duration(e.get("duration"))
            item = {"company": e.get("company") or "", "position": e.get("role") or ""}
            if start:
                item["startDate"] = start
            if end:
                item["endDate"] = end
            highlights = [str(r) for r in (e.get("responsibilities") or [])]
            if highlights:
                item["highlights"] = highlights
            achievements = [str(a) for a in (e.get("achievements") or [])]
            if achievements:
                item["summary"] = "\n".join(achievements)
            # Experience-level projects surface as top-level JSON Resume projects
            for p in e.get("projects") or []:
                if not isinstance(p, dict):
                    continue
                proj = {
                    "name": p.get("name") or "",
                    "description": p.get("outcome") or "",
                    "keywords": [str(t) for t in (p.get("technologies") or [])],
                }
                if p.get("role"):
                    proj["highlights"] = [str(p["role"])]
                resume["projects"].append(proj)
            work.append(item)
    return work


def _build_education(data: dict) -> list:
    education = []
    for e in data.get("education") or []:
        if not isinstance(e, dict):
            continue
        item = {
            "institution": e.get("institution") or "",
            "studyType": e.get("degree") or "",
            "area": e.get("field") or "",
            "score": str(e["cgpa"]) if e.get("cgpa") is not None else "",
        }
        if e.get("year"):
            item["endDate"] = str(e["year"])
        education.append(item)
    return education


def _build_skills(data: dict) -> list:
    skills = []
    raw = data.get("skills") or {}
    if not isinstance(raw, dict):
        raw = {"technical": [str(s) for s in raw] if isinstance(raw, list) else []}
    for key, group_name in _SKILL_GROUPS:
        keywords = [str(k) for k in (raw.get(key) or []) if k]
        if keywords:
            skills.append({"name": group_name, "keywords": keywords})
    return skills


def _build_projects(data: dict) -> list:
    projects = []
    for p in data.get("projects") or []:
        if not isinstance(p, dict):
            continue
        item = {
            "name": p.get("title") or "",
            "description": p.get("problem_statement") or "",
            "keywords": [str(t) for t in (p.get("technologies") or [])],
        }
        highlights = []
        if p.get("your_role"):
            highlights.append(str(p["your_role"]))
        if p.get("impact"):
            highlights.append(str(p["impact"]))
        if highlights:
            item["highlights"] = highlights
        projects.append(item)
    return projects


def _build_certificates(data: dict) -> list:
    certificates = []
    for c in data.get("certifications") or []:
        if not isinstance(c, dict):
            continue
        item = {"name": c.get("name") or "", "issuer": c.get("issuer") or ""}
        if c.get("year"):
            item["date"] = str(c["year"])
        certificates.append(item)
    return certificates


def _build_awards(data: dict) -> list:
    awards = []
    for a in data.get("achievements") or []:
        if isinstance(a, str):
            awards.append({"title": a})
        elif isinstance(a, dict):
            awards.append(
                {
                    "title": a.get("title") or a.get("name") or "",
                    "summary": a.get("description") or a.get("summary") or "",
                }
            )
    # Professional key highlights are folded into awards so they survive
    # the canonical representation and the legacy PDF round-trip.
    for h in data.get("key_highlights") or []:
        if isinstance(h, str):
            awards.append({"title": h})
    return awards


def _build_interests(data: dict) -> list:
    interests = []
    for act in data.get("extra_activities") or []:
        if isinstance(act, str):
            interests.append({"name": act})
        elif isinstance(act, dict):
            interests.append({"name": act.get("name") or ""})
    return interests


def _build_languages(data: dict) -> list:
    languages = []
    for lang in data.get("languages") or []:
        if not isinstance(lang, dict):
            continue
        item = {"language": lang.get("name") or ""}
        fluency = lang.get("fluency") or lang.get("proficiency")
        if fluency:
            item["fluency"] = str(fluency)
        if item.get("language"):
            languages.append(item)
    return languages


# ---------------------------------------------------------------------------
# Reverse adapter: stored JSON Resume -> legacy Jinja template dict (PDF only)
# ---------------------------------------------------------------------------
def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _join_duration(start, end):
    if start and end:
        return f"{start} - {end}"
    return start or end or ""


def resume_json_to_template_data(
    resume_json: dict, resume_type: str = "fresher", template: str = "professional"
) -> dict:
    """Rebuild the legacy template dict from a stored JSON Resume.

    Purpose: the optional PDF endpoint can render a stored resume with the
    existing Jinja templates WITHOUT another AI call. Purely deterministic.
    """
    basics = resume_json.get("basics") or {}
    loc = basics.get("location") or {}
    profiles = {
        str(p.get("network", "")).lower(): str(p.get("url", ""))
        for p in (basics.get("profiles") or [])
        if isinstance(p, dict)
    }
    label = basics.get("label") or ""

    personal_info = {
        "name": basics.get("name") or "",
        "email": basics.get("email") or "",
        "phone": basics.get("phone") or "",
        "designation": label,
        "about_me": "",
        "profile_image": basics.get("image") or "",
        "photo": None,
        "location": "",
        "city": loc.get("city") or "",
        "state": loc.get("region") or "",
        "country": loc.get("countryCode") or "",
        "linkedin": profiles.get("linkedin") or None,
        "github": profiles.get("github") or None,
        "portfolio": profiles.get("portfolio") or profiles.get("web") or None,
    }

    education = []
    for e in resume_json.get("education") or []:
        if not isinstance(e, dict):
            continue
        education.append(
            {
                "institution": e.get("institution") or "",
                "degree": e.get("studyType") or "",
                "field": e.get("area") or "",
                "year": _to_int(e.get("endDate")),
                "cgpa": _to_float(e.get("score")),
            }
        )

    skills = {key: [] for key, _ in _SKILL_GROUPS}
    for s in resume_json.get("skills") or []:
        if not isinstance(s, dict):
            continue
        key = _SKILL_GROUP_TO_KEY.get(str(s.get("name", "")).strip().lower())
        if key:
            skills[key] = [str(k) for k in (s.get("keywords") or [])]

    projects = []
    for p in resume_json.get("projects") or []:
        if not isinstance(p, dict):
            continue
        highlights = [str(h) for h in (p.get("highlights") or [])]
        projects.append(
            {
                "title": p.get("name") or "",
                "problem_statement": p.get("description") or "",
                "your_role": highlights[0] if len(highlights) > 0 else "",
                "technologies": [str(t) for t in (p.get("keywords") or [])],
                "impact": highlights[1] if len(highlights) > 1 else "",
            }
        )

    certifications = []
    for c in resume_json.get("certificates") or []:
        if not isinstance(c, dict):
            continue
        certifications.append(
            {
                "name": c.get("name") or "",
                "issuer": c.get("issuer") or "",
                "year": _to_int(c.get("date")),
            }
        )

    achievements = []
    for a in resume_json.get("awards") or []:
        if isinstance(a, dict):
            title = a.get("title") or ""
            summary = a.get("summary") or ""
            achievements.append(f"{title}: {summary}" if summary and title else title or summary)
        elif isinstance(a, str):
            achievements.append(a)
    achievements = [a for a in achievements if a]

    extra_activities = []
    for i in resume_json.get("interests") or []:
        if isinstance(i, dict) and i.get("name"):
            extra_activities.append(str(i["name"]))

    languages = [
        {"id": "", "name": lang.get("language") or "", "code": ""}
        for lang in resume_json.get("languages") or []
        if isinstance(lang, dict) and lang.get("language")
    ]

    data = {
        "resume_type": resume_type,
        "template": template,
        "personal_info": personal_info,
        "education_meta": {},
        "languages": languages,
        "education": education,
        "skills": skills,
        "projects": projects,
        "certifications": certifications,
        "achievements": achievements,
        "extra_activities": extra_activities,
        "additional_insights": [],
        "strengths": [],
        "preferred_locations": [],
    }

    if resume_type == "fresher":
        data["career_direction"] = {
            "target_role": label,
            "target_industry": "",
            "why_this_role": "",
        }
        data["internships"] = []
        for w in resume_json.get("work") or []:
            if not isinstance(w, dict):
                continue
            data["internships"].append(
                {
                    "company": w.get("company") or "",
                    "duration": _join_duration(w.get("startDate"), w.get("endDate")),
                    "responsibilities": [str(h) for h in (w.get("highlights") or [])],
                    "key_achievement": w.get("summary") or None,
                }
            )
    else:
        data["career_positioning"] = {
            "current_role": label,
            "total_experience": "",
            "target_role": "",
            "target_industry": "",
            "key_expertise": [],
        }
        data["experience"] = []
        for w in resume_json.get("work") or []:
            if not isinstance(w, dict):
                continue
            summary = w.get("summary") or ""
            exp_achievements = [a for a in str(summary).split("\n") if a]
            data["experience"].append(
                {
                    "company": w.get("company") or "",
                    "role": w.get("position") or "",
                    "duration": _join_duration(w.get("startDate"), w.get("endDate")),
                    "responsibilities": [str(h) for h in (w.get("highlights") or [])],
                    "achievements": exp_achievements,
                    "projects": [],
                }
            )
        # Key highlights were folded into awards[] by the forward adapter, so
        # they already surface under achievements after the reverse mapping.
        data["key_highlights"] = []

    return data
