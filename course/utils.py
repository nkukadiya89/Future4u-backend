import re
from difflib import get_close_matches

SYMBOL_MAP = {
    "c++": "cplusplus",
    "c#": "csharp",
    "f#": "fsharp",
    ".net": "dotnet",
}


def normalize_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    for symbol, replacement in SYMBOL_MAP.items():
        text = text.replace(symbol, replacement)
    text = re.sub(r"[/,|&]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return text.strip()


def normalize_list(data):
    return [normalize_text(i) for i in data if i]


def clean(text):
    return re.sub(r"\s+", "", text)


def split_skills(text):
    return [s.strip() for s in re.split(r"[/,|&]", text) if s.strip()]


def is_match(ai_value, course_values):
    ai_parts = split_skills(ai_value)

    for ai_part in ai_parts:
        ai_norm = normalize_text(ai_part)

        if len(ai_norm) < 3:
            continue

        ai_clean = clean(ai_norm)

        for cv in course_values:
            cv_parts = split_skills(cv)

            for cv_part in cv_parts:
                cv_norm = normalize_text(cv_part)

                if len(cv_norm) < 3:
                    continue

                cv_clean = clean(cv_norm)

                # 1. exact match on cleaned
                if ai_clean == cv_clean:
                    return True

                if len(ai_clean) >= 3 and cv_clean:
                    shorter = min(len(ai_clean), len(cv_clean))
                    longer = max(len(ai_clean), len(cv_clean))
                    ratio = shorter / longer
                    if (ai_clean in cv_clean or cv_clean in ai_clean) and ratio >= 0.6:
                        return True

                if len(ai_clean) >= 4:
                    if get_close_matches(ai_clean, [cv_clean], n=1, cutoff=0.75):
                        return True
    return False


def get_next_levels(user_edu):
    mapping = {
        "secondary": ["higher_secondary_11", "higher_secondary", "diploma", "iti"],
        "higher_secondary_11": ["higher_secondary", "diploma"],
        "higher_secondary": ["graduation", "diploma"],
        "iti": ["diploma", "graduation"],
        "diploma": ["graduation"],
        "graduation": ["post_graduation", "professional"],
        "post_graduation": ["doctorate", "professional"],
        "doctorate": [],
        "professional": [],
    }
    return mapping.get(user_edu, [])
