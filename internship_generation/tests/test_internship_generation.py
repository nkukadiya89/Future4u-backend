from __future__ import annotations

from django.test import SimpleTestCase
from pydantic import ValidationError

from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.services.internship_generation_service import _build_response
from internship_generation.services.payload_parser import parse_ai_payload
from internship_generation.utils import word_count


SAMPLE_PAYLOAD = {
    "internship_title": "Software Development Intern",
    "about_internship": (
        "We are looking for a motivated software development intern to join our engineering team. "
        "You will work on real-world backend projects using Python and Django, contributing to APIs "
        "and web application features. This role is ideal for students or recent graduates who want "
        "hands-on experience building production-ready software. You will learn from senior developers, "
        "follow coding best practices, and gain exposure to collaborative development workflows. "
        "Interns should be comfortable learning new tools, asking questions, and taking ownership of "
        "assigned tasks. Join us to strengthen your development skills and build work you can showcase."
    ),
    "key_responsibilities": [
        "Develop backend APIs using Django",
        "Fix bugs and improve application performance",
        "Write unit tests for new features",
        "Participate in code reviews",
        "Collaborate with senior developers on feature delivery",
    ],
    "skills": [
        "Python",
        "Django",
        "REST API",
        "Git",
        "SQL",
        "Docker",
    ],
}


class InternshipGenerationPayloadTests(SimpleTestCase):
    def test_valid_sample_payload(self):
        payload = InternshipGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        self.assertEqual(payload.internship_title, "Software Development Intern")
        self.assertGreaterEqual(word_count(payload.about_internship), 60)
        self.assertLessEqual(word_count(payload.about_internship), 150)
        self.assertEqual(len(payload.key_responsibilities), 5)
        self.assertEqual(len(payload.skills), 6)

    def test_rejects_short_overview(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "about_internship": "Too short overview for validation.",
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_rejects_duplicate_skills(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "skills": ["Python", "Python", "Django", "Git", "SQL", "REST API"],
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_rejects_duplicate_responsibilities(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "key_responsibilities": [
                "Develop backend APIs using Django",
                "Develop backend APIs using Django",
                "Write unit tests for new features",
                "Participate in code reviews",
                "Collaborate with senior developers",
            ],
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_rejects_banned_marketing_phrase(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "about_internship": SAMPLE_PAYLOAD["about_internship"].replace(
                "We are looking",
                "Join our world-class team. We are looking",
            ),
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_rejects_banned_title_phrase(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "internship_title": "Rockstar Developer Intern",
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_rejects_too_few_responsibilities(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "key_responsibilities": SAMPLE_PAYLOAD["key_responsibilities"][:3],
        }
        with self.assertRaises(ValidationError):
            InternshipGenerationPayload.model_validate(bad)

    def test_parser_maps_legacy_aliases(self):
        legacy = {
            "title": "Python Developer Intern",
            "description": SAMPLE_PAYLOAD["about_internship"],
            "responsibilities": SAMPLE_PAYLOAD["key_responsibilities"],
            "requiredSkills": SAMPLE_PAYLOAD["skills"],
        }
        payload = parse_ai_payload(legacy)
        self.assertEqual(payload.internship_title, "Python Developer Intern")

    def test_response_includes_user_fields(self):
        payload = InternshipGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        user_input = {
            "about_internship": "Backend intern role using Python and Django.",
            "department": "Engineering",
            "stipend": "15000",
            "duration": "3 Months",
            "mode": "Remote",
            "application_deadline": None,
        }
        response = _build_response(payload, user_input)
        self.assertEqual(response["department"], user_input["department"])
        self.assertEqual(response["stipend"], user_input["stipend"])
        self.assertEqual(response["duration"], user_input["duration"])
        self.assertEqual(response["mode"], user_input["mode"])
        self.assertEqual(response["internship_title"], payload.internship_title)
