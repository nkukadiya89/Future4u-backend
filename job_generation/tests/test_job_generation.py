from __future__ import annotations

from django.test import SimpleTestCase
from pydantic import ValidationError

from job_generation.schemas.job_output import JobGenerationPayload
from job_generation.services.job_generation_service import _build_response
from job_generation.services.payload_parser import parse_ai_payload
from job_generation.utils import word_count


SAMPLE_PAYLOAD = {
    "name": "Junior Python Developer",
    "description": (
        "We're looking for a Junior Python Developer to build and maintain backend APIs. "
        "You will work with senior engineers and product teams to deliver reliable features."
    ),
    "responsibilities": [
        "Build and maintain Django REST APIs",
        "Write unit tests for backend services",
        "Fix bugs reported by QA teams",
        "Review database queries for performance",
        "Collaborate with frontend developers on APIs",
    ],
    "skills": ["Python", "Django", "SQL", "Git", "REST API"],
    "education_tags": ["Bachelor's Degree"],
    "why_this_match": (
        "Your skills in Python, Django, and SQL align well with this role. "
        "You are a strong match for this opportunity."
    ),
}


class JobGenerationPayloadTests(SimpleTestCase):
    def test_valid_sample_payload(self):
        payload = JobGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        self.assertEqual(payload.name, "Junior Python Developer")
        self.assertGreaterEqual(word_count(payload.description), 20)
        self.assertLessEqual(word_count(payload.description), 40)
        self.assertGreaterEqual(word_count(payload.why_this_match), 15)
        self.assertLessEqual(word_count(payload.why_this_match), 35)
        self.assertEqual(len(payload.responsibilities), 5)
        self.assertEqual(payload.education_tags, ["Bachelor's Degree"])

    def test_accepts_multiple_education_tags(self):
        payload = JobGenerationPayload.model_validate(
            {
                **SAMPLE_PAYLOAD,
                "education_tags": ["BCA", "MCA", "Diploma"],
            }
        )
        self.assertEqual(payload.education_tags, ["BCA", "MCA", "Diploma"])

    def test_coerces_legacy_string_education_tag(self):
        payload = JobGenerationPayload.model_validate(
            {**SAMPLE_PAYLOAD, "education_tags": "bca"}
        )
        self.assertEqual(payload.education_tags, ["bca"])

    def test_accepts_llm_generated_education_labels(self):
        payload = JobGenerationPayload.model_validate(
            {
                **SAMPLE_PAYLOAD,
                "education_tags": ["Integrated M.Sc Data Science", "B.Tech CSE"],
            }
        )
        self.assertEqual(
            payload.education_tags,
            ["Integrated M.Sc Data Science", "B.Tech CSE"],
        )

    def test_rejects_duplicate_education_tags(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "education_tags": ["BCA", "BCA"],
        }
        with self.assertRaises(ValidationError):
            JobGenerationPayload.model_validate(bad)

    def test_rejects_short_description(self):
        bad = {**SAMPLE_PAYLOAD, "description": "Too short description."}
        with self.assertRaises(ValidationError):
            JobGenerationPayload.model_validate(bad)

    def test_rejects_duplicate_skills(self):
        bad = {
            **SAMPLE_PAYLOAD,
            "skills": ["Python", "Python", "Django", "SQL", "Git"],
        }
        with self.assertRaises(ValidationError):
            JobGenerationPayload.model_validate(bad)

    def test_parser_maps_legacy_aliases(self):
        legacy = {
            "title": "Data Analyst",
            "description": SAMPLE_PAYLOAD["description"],
            "responsibilities": SAMPLE_PAYLOAD["responsibilities"],
            "skills": SAMPLE_PAYLOAD["skills"],
            "qualifications": ["Bachelor's Degree"],
            "whyThisMatches": SAMPLE_PAYLOAD["why_this_match"],
        }
        payload = parse_ai_payload(legacy)
        self.assertEqual(payload.name, "Data Analyst")

    def test_response_includes_user_fields(self):
        from datetime import date
        from unittest.mock import Mock

        payload = JobGenerationPayload.model_validate(SAMPLE_PAYLOAD)
        city = Mock()
        city.pk = 42
        city.name = "Hyderabad"
        response = _build_response(
            payload,
            {
                "job_summary": "Hiring a junior Python developer for backend API work.",
                "organization_name": "Future4U Labs",
                "city": city,
                "salary_range": "INR 4-6 LPA",
                "job_type": "full_time",
                "experience_level": "0_1",
                "mode": "hybrid",
                "application_deadline": date(2026, 7, 1),
            },
        )
        self.assertEqual(response["organization_name"], "Future4U Labs")
        self.assertNotIn("job_summary", response)
        self.assertEqual(response["city"], 42)
        self.assertEqual(response["city_name"], "Hyderabad")
        self.assertEqual(response["salary_range"], "INR 4-6 LPA")
        self.assertEqual(response["job_type"], "full_time")
        self.assertEqual(response["experience_level"], "0_1")
        self.assertEqual(response["mode"], "hybrid")
        self.assertEqual(response["application_deadline"], "2026-07-01")
        self.assertEqual(response["name"], "Junior Python Developer")
