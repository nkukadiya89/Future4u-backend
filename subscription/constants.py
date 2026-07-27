# Feature code → Subscription model field
FEATURE_FIELD_MAP = {
    "ai_chat": "ai_chat_access",
    "career_compare": "career_compare",
    "career_roadmap": "career_roadmap",
    "assessment": "no_of_profile_assessment",
    "monthly_tokens": "no_of_tokens",
    "internship_gen": "no_of_internship_access",
    "course_gen": "no_of_course_portal_access",
    "job_gen": "no_of_job_portal_access",
}

# Portal access type + count field pairs
PORTAL_FIELD_MAP = {
    "internship": ("internship_access_type", "no_of_internship_access"),
    "job": ("job_portal_access_type", "no_of_job_portal_access"),
    "course": ("course_portal_access_type", "no_of_course_portal_access"),
    "project_topic": ("project_topic_access_type", "no_of_project_topic_access"),
}
