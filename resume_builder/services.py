"""
Resume Builder service — bridges Django user profiles to the resume PDF generator.

All data is sourced directly from StudentProfile / ProfessionalProfile models
and the related User model. Every available field is mapped.
"""

from __future__ import annotations


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
        "science_track": profile.science_track or None,
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


def generate_resume_pdf(resume_data: dict, skip_ai: bool = False) -> bytes:
    """
    Given a fully-built resume dict, call AI enhancement + PDF generation.
    Returns raw PDF bytes.
    Pass skip_ai=True to bypass AI and use a placeholder summary (for testing).
    """
    from resume_builder.resume_services.ai import (
        enhance_fresher_summary,
        enhance_professional_summary,
    )
    from resume_builder.resume_services.generator import build_resume

    resume_type = resume_data.get("resume_type")

    if skip_ai:
        summary = "Experienced professional seeking to leverage technical skills and domain expertise to deliver impactful results in a dynamic environment."
    elif resume_type == "fresher":
        summary = enhance_fresher_summary(resume_data)
    else:
        summary = enhance_professional_summary(resume_data)

    return build_resume(resume_data, summary)
