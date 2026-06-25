from __future__ import annotations

import json

from django.test import SimpleTestCase
from pydantic import ValidationError

from course_generation.schemas.course_output import CourseGenerationPayload
from course_generation.services.json_response_parser import JsonResponseParser, format_validation_errors


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


class JsonResponseParserTests(SimpleTestCase):
    def setUp(self):
        self.parser = JsonResponseParser()
        self.valid_json = json.dumps(SAMPLE_PAYLOAD)

    def test_parses_clean_json(self):
        result = self.parser.parse_and_validate(self.valid_json, model_class=CourseGenerationPayload)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.extracted_json)
        self.assertIsNone(result.parse_error)
        self.assertIsNone(result.validation_errors)
        self.assertIsInstance(result.validated_model, CourseGenerationPayload)
        self.assertEqual(result.validated_model.course_title, "Python for Data Science")

    def test_parses_markdown_wrapped_json(self):
        wrapped = f"Here is the course JSON:\n```json\n{self.valid_json}\n```\nThanks."
        result = self.parser.parse_and_validate(wrapped, model_class=CourseGenerationPayload)

        self.assertTrue(result.success)
        self.assertEqual(result.validated_model.course_title, "Python for Data Science")

    def test_fails_on_malformed_json(self):
        malformed = '{"course_title": "Python", invalid}'
        result = self.parser.parse_and_validate(malformed, model_class=CourseGenerationPayload)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.parse_error)
        self.assertIn("Invalid JSON", result.parse_error)

    def test_fails_on_missing_fields(self):
        incomplete = json.dumps({"course_title": "Python for Data Science"})
        result = self.parser.parse_and_validate(incomplete, model_class=CourseGenerationPayload)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.validation_errors)
        self.assertIn("course_overview", result.validation_errors)

    def test_strips_value_error_prefix_from_validation_messages(self):
        try:
            CourseGenerationPayload.model_validate({"course_title": "Python"})
        except ValidationError as exc:
            formatted = format_validation_errors(exc)
        else:
            self.fail("Expected validation error")

        self.assertNotIn("Value error,", formatted)
        self.assertIn("course_overview", formatted)
