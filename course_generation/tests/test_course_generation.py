from __future__ import annotations

from django.test import SimpleTestCase
from pydantic import ValidationError

from course_generation.schemas.course_output import CourseGenerationPayload
from course_generation.services.course_generation_service import _build_response
from course_generation.services.payload_parser import parse_ai_payload
from course_generation.utils import word_count


SAMPLE_PAYLOAD = {
    "course_title": "Python for Data Science",
    "course_overview": (
        "This course teaches Python programming from the ground up, with a focus on "
        "data analysis and introductory machine learning. It is designed for students "
        "and working professionals who want practical coding skills without prior experience. "
        "Learners will work with real datasets, write clean code, and build small projects "
        "they can add to a portfolio. By the end, you will be able to load data, analyze "
        "trends, and present insights clearly."
    ),
    "skills": [
        "Python",
        "NumPy",
        "Pandas",
        "Matplotlib",
        "Data Analysis",
        "Machine Learning Basics",
    ],
    "course_content": [
        "Introduction to Python",
        "Variables and Data Types",
        "Control Flow",
        "Functions",
        "NumPy Basics",
        "Pandas for Data Analysis",
        "Data Visualization",
        "Final Project",
    ],
    "why_this_course": (
        "This course helps learners build practical Python and data analysis skills that "
        "are useful for careers in software development, analytics, and machine learning. "
        "It is suitable for beginners as well as professionals looking to upgrade their skills. "
        "You will gain hands-on experience with real datasets and build confidence for job interviews."
    ),
    "certification_info": (
        "A Certificate of Completion will be awarded to all learners after successfully "
        "finishing the course and meeting every assessment requirement set by the institute."
    ),
}


class CourseGenerationPayloadTests(SimpleTestCase):
    def test_valid_sample_payload(self):
        payload = CourseGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        self.assertEqual(payload.course_title, "Python for Data Science")
        self.assertGreaterEqual(word_count(payload.course_overview), 60)
        self.assertLessEqual(word_count(payload.course_overview), 150)
        self.assertGreaterEqual(word_count(payload.why_this_course), 40)
        self.assertLessEqual(word_count(payload.why_this_course), 80)
        self.assertEqual(len(payload.skills), 6)
        self.assertEqual(len(payload.course_content), 8)

    def test_rejects_short_overview(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "course_overview": "Too short overview for validation.",
        }
        with self.assertRaises(ValidationError):
            CourseGenerationPayload.model_validate(bad)

    def test_rejects_duplicate_skills(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "skills": ["Python", "Python", "NumPy", "Pandas", "Matplotlib", "SQL"],
        }
        with self.assertRaises(ValidationError):
            CourseGenerationPayload.model_validate(bad)

    def test_rejects_duplicate_course_content(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "course_content": [
                "Introduction to Python",
                "Introduction to Python",
                "Control Flow",
                "Functions",
                "NumPy Basics",
            ],
        }
        with self.assertRaises(ValidationError):
            CourseGenerationPayload.model_validate(bad)

    def test_rejects_banned_marketing_phrase(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "course_overview": SAMPLE_PAYLOAD["course_overview"].replace(
                "This course teaches",
                "This world-class course teaches",
            ),
        }
        with self.assertRaises(ValidationError):
            CourseGenerationPayload.model_validate(bad)

    def test_rejects_invented_cert_provider(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "certification_info": "Certificate by Google after successful completion.",
        }
        with self.assertRaises(ValidationError):
            CourseGenerationPayload.model_validate(bad)

    def test_parser_maps_legacy_aliases(self):
        legacy = {
            "title": "Data Science with Python",
            "overview": SAMPLE_PAYLOAD["course_overview"],
            "requiredSkills": SAMPLE_PAYLOAD["skills"],
            "modules": SAMPLE_PAYLOAD["course_content"],
            "whyThisCourse": SAMPLE_PAYLOAD["why_this_course"],
            "certificationInfo": SAMPLE_PAYLOAD["certification_info"],
        }
        payload = parse_ai_payload(legacy)
        self.assertEqual(payload.course_title, "Data Science with Python")

    def test_response_includes_user_fields(self):
        payload = CourseGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        user_input = {
            "course_overview": "Learn programming for data science.",
            "course_price": "15000",
            "course_type": "certification",
            "mode": "online",
            "duration": "12 Weeks",
        }
        response = _build_response(payload, user_input)
        self.assertEqual(response["course_price"], user_input["course_price"])
        self.assertEqual(response["course_type"], user_input["course_type"])
        self.assertEqual(response["mode"], user_input["mode"])
        self.assertEqual(response["duration"], user_input["duration"])
        self.assertEqual(response["course_title"], payload.course_title)
        self.assertNotIn("course_overview_input", response)
