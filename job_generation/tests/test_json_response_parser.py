from __future__ import annotations

import json

from django.test import SimpleTestCase

from pydantic import ValidationError

from job_generation.schemas.job_output import JobGenerationPayload
from job_generation.services.json_response_parser import JsonResponseParser, format_validation_errors


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


class JsonResponseParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = JsonResponseParser()
        self.valid_json = json.dumps(SAMPLE_PAYLOAD)

    def test_parses_clean_json(self):
        result = self.parser.parse_and_validate(self.valid_json, model_class=JobGenerationPayload)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.extracted_json)
        self.assertIsNone(result.parse_error)
        self.assertIsNone(result.validation_errors)
        self.assertIsInstance(result.validated_model, JobGenerationPayload)
        self.assertEqual(result.validated_model.name, "Junior Python Developer")

    def test_parses_markdown_wrapped_json(self):
        wrapped = f"Here is the job posting:\n```json\n{self.valid_json}\n```\nThanks."
        result = self.parser.parse_and_validate(wrapped, model_class=JobGenerationPayload)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.extracted_json)
        self.assertIsNone(result.parse_error)
        self.assertEqual(result.validated_model.name, "Junior Python Developer")

    def test_fails_on_malformed_json(self):
        malformed = '{"name": "Developer", invalid}'
        result = self.parser.parse_and_validate(malformed, model_class=JobGenerationPayload)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.parse_error)
        self.assertIn("Invalid JSON", result.parse_error)
        self.assertIsNone(result.validation_errors)

    def test_fails_on_partial_json(self):
        partial = self.valid_json[:120]
        result = self.parser.parse_and_validate(partial, model_class=JobGenerationPayload)

        self.assertFalse(result.success)
        self.assertTrue(
            result.parse_error is not None or result.validation_errors is not None
        )
        self.assertIsNone(result.validated_model)

    def test_fails_on_missing_fields(self):
        incomplete = json.dumps({"name": "Developer"})
        result = self.parser.parse_and_validate(incomplete, model_class=JobGenerationPayload)

        self.assertFalse(result.success)
        self.assertIsNone(result.parse_error)
        self.assertIsNotNone(result.validation_errors)
        self.assertIn("description", result.validation_errors)

    def test_extracts_json_with_leading_and_trailing_text(self):
        noisy = (
            "Sure, here is the JSON you asked for:\n"
            f"{self.valid_json}\n"
            "Let me know if you need changes."
        )
        result = self.parser.parse_and_validate(noisy, model_class=JobGenerationPayload)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.extracted_json)
        self.assertTrue(result.extracted_json.startswith("{"))
        self.assertTrue(result.extracted_json.endswith("}"))

    def test_logs_raw_and_extracted_values_on_failure(self):
        raw = 'prefix {"name": "Broken",}'
        result = self.parser.parse_and_validate(raw, model_class=JobGenerationPayload)

        self.assertEqual(result.raw_llm_response, raw)
        self.assertIsNotNone(result.extracted_json)
        self.assertIsNotNone(result.parse_error)

    def test_strips_value_error_prefix_from_validation_messages(self):
        try:
            JobGenerationPayload.model_validate({"name": "Developer"})
        except ValidationError as exc:
            formatted = format_validation_errors(exc)
        else:
            self.fail("Expected validation error")

        self.assertNotIn("Value error,", formatted)
        self.assertIn("description", formatted)
