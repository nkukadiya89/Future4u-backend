from __future__ import annotations

import re
from typing import Any


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


def count_overview_repeated_items(
    overview: str,
    items: list[str],
    *,
    min_item_words: int = 4,
) -> int:
    """Count list items whose normalized text appears verbatim in the overview."""
    overview_norm = normalize_text(overview)
    repeated = 0
    for item in items:
        item_norm = normalize_text(item)
        if len(item_norm.split()) >= min_item_words and item_norm in overview_norm:
            repeated += 1
    return repeated


def contains_invented_cert_provider(text: str, providers: tuple[str, ...]) -> bool:
    lowered = (text or "").casefold()
    for provider in providers:
        if f"certificate by {provider}" in lowered:
            return True
        if f"certified by {provider}" in lowered:
            return True
    return False
