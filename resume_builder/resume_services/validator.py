"""JSON Resume validator - structural + factual-consistency checks.

Pure function: never mutates the resume, returns a list of error strings
(empty list = valid).
"""

from __future__ import annotations

from resume_builder.resume_services.json_resume import JSON_RESUME_SECTIONS

_LIST_SECTIONS = [
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

# Authoritative profile fields that must match PostgreSQL exactly.
_FACTUAL_BASICS_FIELDS = ("name", "email", "phone")


def validate_json_resume(resume: dict, expected: dict | None = None) -> list:
    """Validate a canonical JSON Resume object.

    Args:
        resume:   the JSON Resume dict produced by to_json_resume().
        expected: optional dict of authoritative values, e.g.
                  {"name": ..., "email": ..., "phone": ...} - when a value is
                  provided and non-empty, the resume must match it exactly.

    Returns a list of error messages (empty when valid).
    """
    errors = []

    if not isinstance(resume, dict):
        return ["resume must be a dict"]

    for section in JSON_RESUME_SECTIONS:
        if section not in resume:
            errors.append(f"missing section: {section}")
        elif section == "basics" and not isinstance(resume[section], dict):
            errors.append("basics must be a dict")
        elif section != "basics" and not isinstance(resume[section], list):
            errors.append(f"{section} must be a list")

    basics = resume.get("basics")
    if isinstance(basics, dict):
        name = basics.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append("basics.name must be a non-empty string")

        if expected:
            for field in _FACTUAL_BASICS_FIELDS:
                authoritative = expected.get(field)
                if authoritative and basics.get(field) != authoritative:
                    errors.append(
                        f"factual mismatch basics.{field}: "
                        f"expected {authoritative!r}, got {basics.get(field)!r}"
                    )

    for section in _LIST_SECTIONS:
        items = resume.get(section)
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section}[{idx}] must be a dict")

    return errors
