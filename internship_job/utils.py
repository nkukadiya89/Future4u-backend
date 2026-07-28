from difflib import get_close_matches

from course.utils import clean, normalize_text, split_skills


def is_match(ai_value, skill_values):
    ai_parts = split_skills(ai_value)

    for ai_part in ai_parts:
        ai_norm = normalize_text(ai_part)

        if len(ai_norm) < 3:
            continue
        ai_clean = clean(ai_norm)

        for cv in skill_values:
            cv_parts = split_skills(cv)

            for cv_part in cv_parts:
                cv_norm = normalize_text(cv_part)

                if len(cv_norm) < 3:
                    continue

                cv_clean = clean(cv_norm)

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
