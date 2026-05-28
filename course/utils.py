import re
from difflib import get_close_matches

def normalize_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s\.]','',text)
    return text

def normalize_list(data):
    return [normalize_text(i) for i in data if i]

def is_match(ai_value, course_values):
    ai_value = normalize_text(ai_value)
    course_values = normalize_list(course_values)
    
    for cv in course_values:
        if ai_value in cv or cv in ai_value:
            return True
        
        match = get_close_matches(ai_value,[cv], n=1, cutoff=0.7)
        if match:
            return True
    return False