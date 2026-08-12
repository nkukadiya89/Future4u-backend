"""
Resume Builder service — bridges Django user profiles to the resume PDF generator.

All data is sourced directly from StudentProfile / ProfessionalProfile models
and the related User model. Every available field is mapped.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _safe_list(value) -> list:
    """Ensure a JSONField value is always a list."""
    if isinstance(value, list):
        return value
    return []


def _safe_str(value) -> str:
    """Return stripped string or empty string."""
    return str(value).strip() if value else ""


def build_student_resume_data(profile, user, template: str = "professional") -> dict:
    """
    Map StudentProfile + User → resume dict.

    Sources every available field from:
      - user.User          : name, email, phone, location, profile_image, about_me, designation
      - StudentProfile     : career_direction, education, skills, projects, internships,
                             certifications, achievements, extra_activities, additional_insights,
                             linkedin_url, github_url, portfolio, science_track, medium,
                             education_level (FK), stream (FK), language (M2M)
    """
    # ── Personal info (User model) ────────────────────────────────────────────
    personal_info = {
        "name": _safe_str(user.full_name)
        or f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "phone": _safe_str(user.phone),
        "about_me": _safe_str(user.about_me),
        "designation": _safe_str(user.designation),
        "profile_image": _safe_str(user.profile_image),
        "location": (
            user.city.name
            if user.city
            else (
                user.states.name
                if user.states
                else (user.country.name if user.country else "")
            )
        ),
        "country": user.country.name if user.country else "",
        "state": user.states.name if user.states else "",
        "city": user.city.name if user.city else "",
        "linkedin": profile.linkedin_url or None,
        "github": profile.github_url or None,
        "portfolio": profile.portfolio or None,
    }

    # ── Education level & stream (FK fields) ──────────────────────────────────
    education_meta = {
        "education_level_code": (
            profile.education_level.level_code if profile.education_level else None
        ),
        "education_level_name": (
            profile.education_level.display_name if profile.education_level else None
        ),
        "stream_code": profile.stream.stream_code if profile.stream else None,
        "stream_name": profile.stream.stream_name if profile.stream else None,
        "science_track": None,
        "medium": profile.medium or None,
    }

    # ── Languages (M2M) ───────────────────────────────────────────────────────
    languages = [
        {"id": str(lang.id), "name": lang.name, "code": lang.code}
        for lang in profile.language.all()
    ]

    # ── Career direction (JSONField) ──────────────────────────────────────────
    raw_cd = _safe_list(profile.career_direction)
    if raw_cd and isinstance(raw_cd[0], dict):
        cd_item = raw_cd[0]
        career_direction = {
            "target_role": cd_item.get("target_role", ""),
            "target_industry": cd_item.get("target_industry", ""),
            "why_this_role": cd_item.get("why_this_role", ""),
        }
    else:
        career_direction = {
            "target_role": "",
            "target_industry": "",
            "why_this_role": "",
        }

    # ── Education (JSONField) ─────────────────────────────────────────────────
    raw_edu = _safe_list(profile.education)
    education = []
    for e in raw_edu:
        if isinstance(e, dict):
            education.append(
                {
                    "institution": e.get("institution", ""),
                    "degree": e.get("degree", ""),
                    "field": e.get("field", ""),
                    "year": int(e.get("year", 0)) if e.get("year") else None,
                    "cgpa": float(e["cgpa"]) if e.get("cgpa") else None,
                }
            )

    # ── Skills (JSONField — dict or list) ─────────────────────────────────────
    raw_skills = profile.skills
    if isinstance(raw_skills, dict):
        skills = {
            "technical": raw_skills.get("technical", []),
            "soft": raw_skills.get("soft", []),
        }
    else:
        skills = {
            "technical": _safe_list(raw_skills),
            "soft": [],
        }

    # ── Projects (JSONField) ──────────────────────────────────────────────────
    raw_projects = _safe_list(profile.projects)
    projects = []
    for p in raw_projects:
        if isinstance(p, dict):
            projects.append(
                {
                    "title": p.get("title", ""),
                    "problem_statement": p.get("problem_statement", ""),
                    "your_role": p.get("your_role", ""),
                    "technologies": p.get("technologies", []),
                    "impact": p.get("impact", ""),
                }
            )

    # ── Internships (JSONField) ───────────────────────────────────────────────
    raw_internships = _safe_list(profile.internships)
    internships = []
    for i in raw_internships:
        if isinstance(i, dict):
            internships.append(
                {
                    "company": i.get("company", ""),
                    "duration": i.get("duration", ""),
                    "responsibilities": i.get("responsibilities", []),
                    "key_achievement": i.get("key_achievement", None),
                }
            )

    # ── Certifications (JSONField) ────────────────────────────────────────────
    raw_certs = _safe_list(profile.certifications)
    certifications = []
    for c in raw_certs:
        if isinstance(c, dict):
            certifications.append(
                {
                    "name": c.get("name", ""),
                    "issuer": c.get("issuer", ""),
                    "year": int(c.get("year", 0)) if c.get("year") else None,
                }
            )

    return {
        "resume_type": "fresher",
        "template": template,
        "personal_info": personal_info,
        "education_meta": education_meta,
        "languages": languages,
        "career_direction": career_direction,
        "education": education,
        "skills": skills,
        "projects": projects,
        "internships": internships,
        "certifications": certifications,
        "achievements": _safe_list(profile.achievements),
        "extra_activities": _safe_list(profile.extra_activities),
        "additional_insights": _safe_list(profile.additional_insights),
        "strengths": [],
        "preferred_locations": [],
    }


def build_professional_resume_data(
    profile, user, template: str = "professional"
) -> dict:
    """
    Map ProfessionalProfile + User → resume dict.

    Sources every available field from:
      - user.User              : name, email, phone, location, profile_image, about_me, designation
      - ProfessionalProfile    : employment_type, years_of_experience, current_job_title,
                                 current_industry, company_size, career_direction, education,
                                 work_experience, skills, certifications, key_highlights,
                                 additional_insights, linkedin_url, github_url, portfolio,
                                 education_level (FK), language (M2M)
    """
    # ── Personal info (User model) ────────────────────────────────────────────
    personal_info = {
        "name": _safe_str(user.full_name)
        or f"{user.first_name} {user.last_name}".strip(),
        "email": user.email,
        "phone": _safe_str(user.phone),
        "about_me": _safe_str(user.about_me),
        "designation": _safe_str(user.designation),
        "profile_image": _safe_str(user.profile_image),
        "location": (
            user.city.name
            if user.city
            else (
                user.states.name
                if user.states
                else (user.country.name if user.country else "")
            )
        ),
        "country": user.country.name if user.country else "",
        "state": user.states.name if user.states else "",
        "city": user.city.name if user.city else "",
        "linkedin": profile.linkedin_url or None,
        "github": profile.github_url or None,
        "portfolio": profile.portfolio or None,
    }

    # ── Education level (FK) ──────────────────────────────────────────────────
    education_meta = {
        "education_level_code": (
            profile.education_level.level_code if profile.education_level else None
        ),
        "education_level_name": (
            profile.education_level.display_name if profile.education_level else None
        ),
        "employment_type": profile.employment_type or None,
        "company_size": profile.company_size or None,
    }

    # ── Languages (M2M) ───────────────────────────────────────────────────────
    languages = [
        {"id": str(lang.id), "name": lang.name, "code": lang.code}
        for lang in profile.language.all()
    ]

    # ── Career positioning (direct fields + career_direction JSONField) ───────
    raw_cd = _safe_list(profile.career_direction)
    if raw_cd and isinstance(raw_cd[0], dict):
        cd_item = raw_cd[0]
        career_positioning = {
            "current_role": profile.current_job_title
            or cd_item.get("current_role", ""),
            "total_experience": profile.years_of_experience
            or cd_item.get("total_experience", ""),
            "target_role": cd_item.get("target_role", ""),
            "target_industry": cd_item.get(
                "target_industry", profile.current_industry or ""
            ),
            "key_expertise": cd_item.get("key_expertise", [])[:5],
        }
    else:
        career_positioning = {
            "current_role": profile.current_job_title or "",
            "total_experience": profile.years_of_experience or "",
            "target_role": "",
            "target_industry": profile.current_industry or "",
            "key_expertise": [],
        }

    # ── Work experience (JSONField) ───────────────────────────────────────────
    raw_exp = _safe_list(profile.work_experience)
    experience = []
    for e in raw_exp:
        if isinstance(e, dict):
            experience.append(
                {
                    "company": e.get("company", ""),
                    "role": e.get("role", ""),
                    "duration": e.get("duration", ""),
                    "responsibilities": e.get("responsibilities", []),
                    "achievements": e.get("achievements", []),
                    "projects": [
                        {
                            "name": p.get("name", ""),
                            "role": p.get("role", ""),
                            "outcome": p.get("outcome", ""),
                            "technologies": p.get("technologies", []),
                        }
                        for p in e.get("projects", [])
                        if isinstance(p, dict)
                    ],
                }
            )

    # ── Skills (JSONField — dict or list) ─────────────────────────────────────
    raw_skills = profile.skills
    if isinstance(raw_skills, dict):
        skills = {
            "technical": raw_skills.get("technical", []),
            "tools": raw_skills.get("tools", []),
            "domain_knowledge": raw_skills.get("domain_knowledge", []),
            "leadership": raw_skills.get("leadership", []),
        }
    else:
        skills = {
            "technical": _safe_list(raw_skills),
            "tools": [],
            "domain_knowledge": [],
            "leadership": [],
        }

    # ── Education (JSONField) ─────────────────────────────────────────────────
    raw_edu = _safe_list(profile.education)
    education = []
    for e in raw_edu:
        if isinstance(e, dict):
            education.append(
                {
                    "institution": e.get("institution", ""),
                    "degree": e.get("degree", ""),
                    "field": e.get("field", ""),
                    "year": int(e.get("year", 0)) if e.get("year") else None,
                    "cgpa": float(e["cgpa"]) if e.get("cgpa") else None,
                }
            )

    # ── Certifications (JSONField) ────────────────────────────────────────────
    raw_certs = _safe_list(profile.certifications)
    certifications = []
    for c in raw_certs:
        if isinstance(c, dict):
            certifications.append(
                {
                    "name": c.get("name", ""),
                    "issuer": c.get("issuer", ""),
                    "year": int(c.get("year", 0)) if c.get("year") else None,
                }
            )

    return {
        "resume_type": "professional",
        "template": template,
        "personal_info": personal_info,
        "education_meta": education_meta,
        "languages": languages,
        "career_positioning": career_positioning,
        "experience": experience,
        "skills": skills,
        "education": education,
        "certifications": certifications,
        "key_highlights": _safe_list(profile.key_highlights),
        "additional_insights": _safe_list(profile.additional_insights),
        "additional_data": None,
    }


def build_child_resume_data(child, template: str = "professional") -> dict:
    """
    Map ChildProfile → resume dict.

    Sources every available field from ChildProfile directly (no User model).
    Mirrors build_student_resume_data but reads from ChildProfile fields.
    """
    # ── Personal info (ChildProfile fields) ───────────────────────────────────
    personal_info = {
        "name": _safe_str(f"{child.first_name} {child.last_name}".strip()),
        "email": child.email or "",
        "phone": _safe_str(child.phone),
        "about_me": "",
        "designation": "",
        "profile_image": _safe_str(child.profile_image),
        "location": "",
        "country": "",
        "state": "",
        "city": "",
        "linkedin": child.linkedin_url or None,
        "github": child.github_url or None,
        "portfolio": child.portfolio or None,
    }

    # ── Education level & stream (FK fields) ──────────────────────────────────
    education_meta = {
        "education_level_code": (
            child.education_level.level_code if child.education_level else None
        ),
        "education_level_name": (
            child.education_level.display_name if child.education_level else None
        ),
        "stream_code": child.stream.stream_code if child.stream else None,
        "stream_name": child.stream.stream_name if child.stream else None,
        "science_track": None,
        "medium": None,
    }

    # ── Languages (M2M) ───────────────────────────────────────────────────────
    languages = [
        {"id": str(lang.id), "name": lang.name, "code": lang.code}
        for lang in child.language.all()
    ]

    # ── Career direction (JSONField) ──────────────────────────────────────────
    raw_cd = _safe_list(child.career_direction)
    if raw_cd and isinstance(raw_cd[0], dict):
        cd_item = raw_cd[0]
        career_direction = {
            "target_role": cd_item.get("target_role", ""),
            "target_industry": cd_item.get("target_industry", ""),
            "why_this_role": cd_item.get("why_this_role", ""),
        }
    else:
        career_direction = {
            "target_role": "",
            "target_industry": "",
            "why_this_role": "",
        }

    # ── Education (JSONField) ─────────────────────────────────────────────────
    raw_edu = _safe_list(child.education)
    education = []
    for e in raw_edu:
        if isinstance(e, dict):
            education.append(
                {
                    "institution": e.get("institution", ""),
                    "degree": e.get("degree", ""),
                    "field": e.get("field", ""),
                    "year": int(e.get("year", 0)) if e.get("year") else None,
                    "cgpa": float(e["cgpa"]) if e.get("cgpa") else None,
                }
            )

    # ── Skills (JSONField) ────────────────────────────────────────────────────
    raw_skills = child.skills
    if isinstance(raw_skills, dict):
        skills = {
            "technical": raw_skills.get("technical", []),
            "soft": raw_skills.get("soft", []),
        }
    else:
        skills = {
            "technical": _safe_list(raw_skills),
            "soft": [],
        }

    # ── Projects (JSONField) ──────────────────────────────────────────────────
    raw_projects = _safe_list(child.projects)
    projects = []
    for p in raw_projects:
        if isinstance(p, dict):
            projects.append(
                {
                    "title": p.get("title", ""),
                    "problem_statement": p.get("problem_statement", ""),
                    "your_role": p.get("your_role", ""),
                    "technologies": p.get("technologies", []),
                    "impact": p.get("impact", ""),
                }
            )

    # ── Internships (JSONField) ───────────────────────────────────────────────
    raw_internships = _safe_list(child.internships)
    internships = []
    for i in raw_internships:
        if isinstance(i, dict):
            internships.append(
                {
                    "company": i.get("company", ""),
                    "duration": i.get("duration", ""),
                    "responsibilities": i.get("responsibilities", []),
                    "key_achievement": i.get("key_achievement", None),
                }
            )

    # ── Certifications (JSONField) ────────────────────────────────────────────
    raw_certs = _safe_list(child.certifications)
    certifications = []
    for c in raw_certs:
        if isinstance(c, dict):
            certifications.append(
                {
                    "name": c.get("name", ""),
                    "issuer": c.get("issuer", ""),
                    "year": int(c.get("year", 0)) if c.get("year") else None,
                }
            )

    return {
        "resume_type": "fresher",
        "template": template,
        "personal_info": personal_info,
        "education_meta": education_meta,
        "languages": languages,
        "career_direction": career_direction,
        "education": education,
        "skills": skills,
        "projects": projects,
        "internships": internships,
        "certifications": certifications,
        "achievements": _safe_list(child.achievements),
        "extra_activities": _safe_list(child.extra_activities),
        "additional_insights": _safe_list(child.additional_insights),
        "strengths": [],
        "preferred_locations": [],
    }


# Keys the AI must never rewrite — identity/lookup data that has to stay
# exactly as stored (a hallucinated phone number or stream name is worse
# than an unpolished one).
_PROTECTED_KEYS = {
    "personal_info",
    "template",
    "resume_type",
    "education_meta",
    "languages",
}

# Fallback keys for list-of-dict entries the AI adds beyond the profile data,
# so the Jinja templates never hit an UndefinedError for a missing key.
_ENTRY_DEFAULTS = {
    "experience": {
        "company": "",
        "role": "",
        "duration": "",
        "responsibilities": [],
        "achievements": [],
        "projects": [],
    },
    "internships": {
        "company": "",
        "duration": "",
        "responsibilities": [],
        "key_achievement": "",
    },
    "projects": {
        "title": "",
        "problem_statement": "",
        "your_role": "",
        "technologies": [],
        "impact": "",
    },
    "education": {
        "institution": "",
        "degree": "",
        "field": "",
        "year": None,
        "cgpa": None,
    },
    "certifications": {"name": "", "issuer": "", "year": None},
}


def _non_empty(value) -> bool:
    """True when a value is not None / empty string / empty list / empty dict."""
    return value not in (None, "", [], {})


def _merge_llm_dict(base_dict: dict, llm_dict: dict) -> dict:
    """Key-preserving merge for dict sections.

    Base keys always survive; the LLM only overrides keys it provides with
    a non-empty value. Nested dicts/lists are merged the same way.
    """
    merged = dict(base_dict)
    for key, value in llm_dict.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_llm_dict(merged[key], value)
        elif isinstance(value, list) and isinstance(merged.get(key), list):
            merged[key] = _merge_llm_list(merged[key], value, _ENTRY_DEFAULTS.get(key))
        elif _non_empty(value):
            merged[key] = value
    return merged


def _merge_llm_list(base_list: list, llm_list: list, entry_defaults: dict | None) -> list:
    """Merge a list section.

    For dict entries, each LLM entry is merged over its index-aligned base
    entry (or the section defaults when the AI adds new entries), so the
    template-required keys always exist. Scalar lists simply take the
    LLM's non-empty values.
    """
    if not llm_list:
        return base_list

    if any(isinstance(item, dict) for item in llm_list):
        base_entries = [item for item in base_list if isinstance(item, dict)]
        merged_entries = []
        for idx, item in enumerate(llm_list):
            if not isinstance(item, dict):
                continue
            seed = (
                base_entries[idx]
                if idx < len(base_entries)
                else dict(entry_defaults or {})
            )
            merged_entries.append(_merge_llm_dict(seed, item))
        return merged_entries

    return [item for item in llm_list if isinstance(item, (str, int, float))]


def _merge_llm_resume_data(base: dict, llm: dict) -> dict:
    """
    Merge LLM-written content over the profile-derived resume data.

    The LLM output wins for every *content* section (summary, career
    direction, experience, skills, projects, etc.), but only when it provides
    a non-empty value of the right type. Factual/structural keys in
    _PROTECTED_KEYS always come from the profile, and unknown keys are
    ignored so the AI can never inject arbitrary data into the PDF.
    """
    merged = dict(base)

    if not isinstance(llm, dict):
        return merged

    # Summary is only produced by the AI — always take it when present.
    summary = llm.get("summary")
    if isinstance(summary, str) and summary.strip():
        merged["summary"] = summary.strip()

    for key, value in llm.items():
        if key in _PROTECTED_KEYS or key == "summary" or key not in base:
            continue
        if not _non_empty(value):
            continue

        base_value = base.get(key)
        if isinstance(base_value, list):
            if isinstance(value, list):
                merged[key] = _merge_llm_list(
                    base_value, value, _ENTRY_DEFAULTS.get(key)
                )
        elif isinstance(base_value, dict):
            if isinstance(value, dict):
                merged[key] = _merge_llm_dict(base_value, value)
        elif isinstance(base_value, str):
            if isinstance(value, str):
                merged[key] = value.strip()
        elif base_value is None and isinstance(value, (str, list, dict)):
            merged[key] = value

    return merged


def generate_resume_pdf(resume_data: dict, skip_ai: bool = False) -> tuple[bytes, int]:
    """
    Given a fully-built resume dict, enhance ALL content via the LLM and
    generate the PDF. Returns raw PDF bytes and the LLM token usage.
    Pass skip_ai=True to bypass AI (for testing).
    """
    from resume_builder.resume_services.ai import enhance_resume_content
    from resume_builder.resume_services.generator import build_resume

    if skip_ai:
        summary = ""
        token_usage = 0
        final_data = dict(resume_data)
    else:
        llm_content, token_usage = enhance_resume_content(resume_data)
        final_data = _merge_llm_resume_data(resume_data, llm_content)
        summary = final_data.get("summary", "") or ""

    return build_resume(final_data, summary), token_usage


# ---------------------------------------------------------------------------
# Path B — JSON Resume generation orchestrator
# ---------------------------------------------------------------------------
class ResumeTokenError(Exception):
    """Raised when the token pre-check fails (maps to HTTP 402)."""


class ResumeValidationError(Exception):
    """Raised when the final JSON Resume fails validation (maps to HTTP 422)."""


class ResumeEditError(Exception):
    """Raised when an in-place resume edit is invalid (maps to HTTP 400)."""


def apply_resume_edits(record, edits: dict) -> dict:
    """Merge user edits into a stored GeneratedResume.resume_json in place.

    Semantics:
      - Only keys present in `edits` change; everything else stays untouched.
      - List sections (work, education, projects, ...) are REPLACED wholesale
        when provided.
      - basics is deep-merged per key (so sending only
        {"basics": {"summary": "..."}} keeps name/email/phone intact).
      - Unknown top-level keys are rejected so the stored structure stays
        canonical and the PDF round-trip never breaks.

    No AI call, no token deduction — this is a pure database update.

    Raises:
        ResumeEditError:      unknown section / wrong type (HTTP 400)
        ResumeValidationError: merged resume fails structural validation (HTTP 422)
    """
    from copy import deepcopy

    from resume_builder.resume_services.json_resume import JSON_RESUME_SECTIONS
    from resume_builder.resume_services.validator import validate_json_resume

    if not isinstance(edits, dict):
        raise ResumeEditError("edits must be a JSON object")

    merged = deepcopy(record.resume_json)

    for section, value in edits.items():
        if section == "basics":
            if not isinstance(value, dict):
                raise ResumeEditError("basics must be a JSON object")
            merged.setdefault("basics", {}).update(deepcopy(value))
        elif section in JSON_RESUME_SECTIONS:
            if not isinstance(value, list):
                raise ResumeEditError(f"{section} must be a JSON array")
            merged[section] = deepcopy(value)
        else:
            raise ResumeEditError(
                f"Unknown resume section: {section}. Allowed: "
                f"{', '.join(sorted(JSON_RESUME_SECTIONS))}."
            )

    # Re-validate the merged structure so bad edits can never break the PDF.
    errors = validate_json_resume(merged)
    if errors:
        raise ResumeValidationError(errors)

    return merged


_DEDUPE_WINDOW_SECONDS = 30


def _find_recent_generation(user, template: str, resume_type: str, expected_name=None):
    """Return a very recent identical generation, if any (double-click guard).

    The dedupe key includes the source profile name so a parent generating for
    two different children can never collide.
    """
    from datetime import timedelta

    from django.utils import timezone

    from resume_builder.models import GeneratedResume

    cutoff = timezone.now() - timedelta(seconds=_DEDUPE_WINDOW_SECONDS)
    queryset = GeneratedResume.objects.filter(
        user=user,
        template=template,
        resume_type=resume_type,
        deleted=False,
        created_at__gte=cutoff,
    )
    if expected_name:
        queryset = queryset.filter(resume_json__basics__name=expected_name)
    return queryset.order_by("-created_at", "-id").first()


def generate_resume_json(
    profile,
    user,
    resume_type: str,
    template: str = "professional",
    request=None,
):
    """Run the full Path B pipeline and return a stored GeneratedResume.

    Pipeline: build data -> token pre-check -> Groq -> protected merge -> JSON
    Resume -> validate -> store -> deduct actual tokens.

    Raises:
        ResumeTokenError:      insufficient tokens (HTTP 402)
        ResumeValidationError: final JSON Resume failed validation (HTTP 422)
        ValueError:            AI provider failure / invalid template (HTTP 400/500/503)
    """
    from utils.token_check import check_token_available, deduct_monthly_tokens

    from resume_builder.models import GeneratedResume, ResumeTemplate
    from resume_builder.resume_services.ai import enhance_resume_content
    from resume_builder.resume_services.json_resume import to_json_resume
    from resume_builder.resume_services.validator import validate_json_resume

    # Defensive allowlist — the API view validates first, but direct callers
    # (admin, scripts, future reuse) must never persist an arbitrary template.
    if not ResumeTemplate.objects.filter(
        code=template, is_active=True, deleted=False
    ).exists():
        raise ValueError(f"Invalid template: {template!r}")

    # Authoritative identity — used by both the dedupe guard and validation.
    if resume_type == "child":
        expected = {
            "name": f"{profile.first_name} {profile.last_name}".strip(),
            "email": profile.email or "",
            "phone": profile.phone or "",
        }
    else:
        expected = {
            "name": user.full_name or f"{user.first_name} {user.last_name}".strip(),
            "email": user.email or "",
            "phone": user.phone or "",
        }

    # Double-click guard: reuse a very recent identical generation.
    recent = _find_recent_generation(
        user, template, resume_type, expected.get("name")
    )
    if recent:
        return recent

    # 1. Build the Future4U resume source data (existing builders).
    if resume_type == "fresher":
        data = build_student_resume_data(profile, user, template=template)
    elif resume_type == "child":
        data = build_child_resume_data(profile, template=template)
    else:
        data = build_professional_resume_data(profile, user, template=template)

    # 2. Token pre-check (never call Groq when tokens are insufficient).
    try:
        check_token_available(user, "resume_enhance")
    except Exception as exc:
        raise ResumeTokenError(str(exc)) from exc

    # 3. Groq LLM — generates/enhances CONTENT only (existing pipeline).
    llm_content, token_usage = enhance_resume_content(data)

    # 4. Protected merge — profile facts always win (existing logic).
    merged = _merge_llm_resume_data(data, llm_content)

    # 5. Convert to the canonical JSON Resume (deterministic adapter).
    resume_json = to_json_resume(merged)

    # 6. Validate — do not store / deduct on invalid output.
    errors = validate_json_resume(resume_json, expected=expected)
    if errors:
        logger.error(
            "JSON Resume validation failed user=%s type=%s errors=%s",
            user.id,
            resume_type,
            errors,
        )
        raise ResumeValidationError(errors)

    # 7. Store the canonical resume (history preserved — never latest-only).
    record = GeneratedResume.objects.create(
        user=user,
        template=template,
        resume_json=resume_json,
        tokens_used=token_usage or 0,
        resume_type=resume_type,
        created_by=user,
    )

    # 8. Deduct actual token usage only after a successful, stored generation.
    try:
        deduct_monthly_tokens(
            user, token_usage or 0, feature_code="resume_enhance", request=request
        )
    except Exception as exc:
        logger.error(
            "TOKEN_RECONCILE user=%s feature=resume_enhance cost=%s err=%s",
            user.id,
            token_usage,
            exc,
        )
    return record
