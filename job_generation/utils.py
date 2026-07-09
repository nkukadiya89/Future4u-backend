from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Education tag metadata resolution
# ---------------------------------------------------------------------------

# Order matters: more specific patterns first.
_EDUCATION_LEVEL_RULES: list[tuple[tuple[str, ...], str, str]] = [
    # Post-doctoral / PhD / Doctorate
    (("ph.d", "phd", "doctorate", "doctoral"), "Doctorate", "phd"),
    # Post-graduation / Master's
    (
        ("m.tech", "m.e.", "m.eng", "mtech", "m.sc", "msc", "mba", "m.b.a",
         "m.a.", " ma ", "master", "post grad", "postgrad", "pg diploma",
         "pgdm", "m.phil", "mphil", "m.com", "mcom", "mca", "m.c.a"),
        "Post Graduation",
        "post_graduation",
    ),
    # Graduation / Bachelor's
    (
        ("b.tech", "b.e.", "b.eng", "btech", "b.sc", "bsc", "bca", "b.c.a",
         "b.a.", " ba ", "bachelor", "b.com", "bcom", "b.b.a", "bba",
         "b.arch", "b.des", "b.pharma", "b.pharma", "llb", "b.ed", "bed",
         "b.voc", "graduation"),
        "Graduation",
        "graduation",
    ),
    # Diploma / Polytechnic
    (
        ("diploma", "polytechnic", "certificate course", "vocational"),
        "Diploma",
        "diploma",
    ),
    # Class 12 / Higher secondary
    (
        ("12th", "class 12", "hsc", "higher secondary", "intermediate",
         "10+2", "10 + 2", "class xii"),
        "Class 12th",
        "class_12",
    ),
    # Class 10 / Secondary
    (
        ("10th", "class 10", "ssc", "secondary school", "matriculation",
         "class x"),
        "Class 10th",
        "class_10",
    ),
]

_DEFAULT_TYPE = "Graduation"
_DEFAULT_LEVEL_KEY = "graduation"


def resolve_education_tag_meta(tag: str) -> dict[str, str]:
    """Return ``{"name": tag, "type": ..., "level_key": ...}`` for a plain tag string."""
    tag_lower = tag.lower()
    for keywords, edu_type, level_key in _EDUCATION_LEVEL_RULES:
        if any(kw in tag_lower for kw in keywords):
            return {"name": tag, "type": edu_type, "level_key": level_key}
    # Fallback to Graduation when no rule matches
    return {"name": tag, "type": _DEFAULT_TYPE, "level_key": _DEFAULT_LEVEL_KEY}


def clip(value: object, max_len: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def contains_banned_phrase(text: str, banned_phrases: tuple[str, ...]) -> bool:
    return find_banned_phrase(text, banned_phrases) is not None


def find_banned_phrase(text: str, banned_phrases: tuple[str, ...]) -> str | None:
    lowered = (text or "").casefold()
    for phrase in banned_phrases:
        if phrase and phrase in lowered:
            return phrase
    return None


def contains_placeholder(text: str, disallowed: tuple[str, ...]) -> bool:
    lowered = (text or "").casefold()
    return any(p in lowered for p in disallowed if p)


def has_broken_punctuation(text: str) -> bool:
    if ", ," in text:
        return True
    if re.search(r"\[\s*\]", text):
        return True
    if re.search(r"\(\s*\)", text):
        return True
    return False


def deduplicate(items: list[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        key = " ".join(text.casefold().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().casefold())


def sentences(text: str) -> list[str]:
    raw = re.split(r"[.!?]\s+", (text or "").strip())
    return [s.strip() for s in raw if s.strip()]
