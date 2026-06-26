from __future__ import annotations

import json

from django.test import SimpleTestCase
from pydantic import ValidationError

from internship_generation.schemas.internship_output import InternshipGenerationPayload
from internship_generation.services.json_response_parser import (
    JsonResponseParser,
    format_validation_errors,
)


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


class JsonResponseParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = JsonResponseParser()
        self.valid_json = json.dumps(SAMPLE_PAYLOAD)

    def test_parses_clean_json(self):
        result = self.parser.parse_and_validate(
            self.valid_json, model_class=InternshipGenerationPayload
        )

        self.assertTrue(result.success)
        self.assertIsNotNone(result.extracted_json)
        self.assertIsNone(result.parse_error)
        self.assertIsNone(result.validation_errors)
        self.assertIsInstance(result.validated_model, InternshipGenerationPayload)
        self.assertEqual(result.validated_model.internship_title, "Software Development Intern")

    def test_parses_markdown_wrapped_json(self):
        wrapped = f"Here is the internship JSON:\n```json\n{self.valid_json}\n```\nThanks."
        result = self.parser.parse_and_validate(
            wrapped, model_class=InternshipGenerationPayload
        )

        self.assertTrue(result.success)
        self.assertEqual(result.validated_model.internship_title, "Software Development Intern")

    def test_fails_on_malformed_json(self):
        malformed = '{"internship_title": "Python", invalid}'
        result = self.parser.parse_and_validate(
            malformed, model_class=InternshipGenerationPayload
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.parse_error)
        self.assertIn("Invalid JSON", result.parse_error)

    def test_fails_on_missing_fields(self):
        incomplete = json.dumps({"internship_title": "Software Development Intern"})
        result = self.parser.parse_and_validate(
            incomplete, model_class=InternshipGenerationPayload
        )

        self.assertFalse(result.success)
        self.assertIsNotNone(result.validation_errors)
        self.assertIn("about_internship", result.validation_errors)

    def test_strips_value_error_prefix_from_validation_messages(self):
        try:
            InternshipGenerationPayload.model_validate({"internship_title": "Python Intern"})
        except ValidationError as exc:
            formatted = format_validation_errors(exc)
        else:
            self.fail("Expected validation error")

        self.assertNotIn("Value error,", formatted)
        self.assertIn("about_internship", formatted)
