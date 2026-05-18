from __future__ import annotations

from typing import Any

CAREER_ROADMAP_PHASE_KEYS: tuple[str, ...] = (
    "next_3_months",
    "next_3_to_6_months",
    "next_6_to_9_months",
    "next_9_to_12_months",
)

_LEGACY_ROADMAP_KEYS: tuple[str, ...] = (
    "next_3_months",
    "next_6_to_12_months",
    "next_12_to_18_months",
)


def _task(title: str, description: str) -> dict[str, str]:
    return {"task_title": title.strip(), "task_description": description.strip()}


def _title_from_step(description: str) -> str:
    text = description.strip()
    if not text:
        return "Next focus"
    for sep in (" — ", " - ", ". ", "; "):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
    words = text.split()
    if len(words) <= 7:
        title = text
    else:
        title = " ".join(words[:6])
    return title[:60].rstrip(".,;:") or "Next focus"


def normalize_career_roadmap(roadmap: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    """Ensure four 3-month phases; accept legacy 18-month keys from older AI output."""
    if all(roadmap.get(key) for key in CAREER_ROADMAP_PHASE_KEYS):
        return {
            key: list(roadmap.get(key) or [])[:2]
            for key in CAREER_ROADMAP_PHASE_KEYS
        }

    ordered: list[dict[str, str]] = []
    seen: set[str] = set()
    for key in _LEGACY_ROADMAP_KEYS + CAREER_ROADMAP_PHASE_KEYS:
        for item in roadmap.get(key) or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("task_title") or "").strip()
            description = str(item.get("task_description") or "").strip()
            if not description:
                continue
            dedupe_key = description.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            ordered.append(
                _task(title or _title_from_step(description), description)
            )

    while len(ordered) < 4 and ordered:
        ordered.append(ordered[-1])

    if len(ordered) < 4:
        return {
            key: list(roadmap.get(key) or [])
            for key in CAREER_ROADMAP_PHASE_KEYS
            if key in roadmap
        }

    return {
        CAREER_ROADMAP_PHASE_KEYS[index]: [ordered[index]]
        for index in range(4)
    }
