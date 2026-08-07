from __future__ import annotations

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from domain.models import Domain
from project_recommendation.exceptions import (
    ProjectRecommendationAccessDeniedError,
    ProjectRecommendationConfigurationError,
)
from project_recommendation.models import ProjectRecommendation
from project_recommendation.schemas.project_output import ProjectRecommendationPayload
from project_recommendation.services.project_generator import ProjectGenerator
from project_recommendation.services.project_service import ProjectRecommendationService

User = get_user_model()


def _make_payload() -> ProjectRecommendationPayload:
    """Build a valid payload with exactly 3 projects."""
    return ProjectRecommendationPayload(
        projects=[
            {
                "project_name": f"AI Portfolio Builder {i}",
                "short_description": (
                    "Build a portfolio app that showcases projects with "
                    "AI-powered summaries and analytics dashboards."
                ),
                "difficulty": "Beginner",
                "estimated_duration": "2 Weeks",
                "industry_relevance": "Technology and software development",
                "skills_gained": ["Python", "Django", "HTML", "CSS", "Git"],
                "deliverables": ["Repo", "Deploy", "Docs", "Demo", "Report"],
                "portfolio_value": "Demonstrates full-stack and AI integration ability",
                "why_this_project": "High demand skills with clear portfolio impact",
            }
            for i in range(3)
        ]
    )


class ProjectRecommendationServiceTests(TestCase):
    """Service is standalone: generates from domain/category/overview only."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pr_tester@example.com",
            username="pr_tester",
            password="pass12345",
        )
        self.service = ProjectRecommendationService()

    def test_generate_persists_full_response(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator,
            "generate",
            return_value=(payload, 1234),
        ):
            response, token_usage = self.service.generate(
                user=self.user,
                domain="Software Development",
                domain_category="Technology",
                overview="Build a career app",
            )

        self.assertEqual(token_usage, 1234)
        self.assertEqual(response["domain"], "Software Development")
        self.assertEqual(response["domain_category"], "Technology")
        self.assertNotIn("assessment_id", response)
        self.assertEqual(response["overview"], "Build a career app")
        self.assertEqual(len(response["projects"]), 3)

        record = ProjectRecommendation.objects.get(user=self.user)
        self.assertEqual(
            record.profile_type, ProjectRecommendation.ProfileType.STUDENT
        )
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.domain, "Software Development")
        self.assertEqual(record.domain_category, "Technology")
        self.assertEqual(record.overview, "Build a career app")
        self.assertEqual(record.token_usage, 1234)
        self.assertIsNotNone(record.last_recommended_at)
        self.assertEqual(record.created_by, self.user)
        # Full AI payload stored verbatim
        self.assertEqual(record.raw_ai_response, payload.model_dump())
        self.assertEqual(len(record.raw_ai_response["projects"]), 3)

    def test_generate_upserts_same_input(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 100)
        ):
            self.service.generate(
                user=self.user,
                domain="Software Development",
                domain_category="Technology",
            )
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 200)
        ):
            self.service.generate(
                user=self.user,
                domain="Software Development",
                domain_category="Technology",
            )

        self.assertEqual(ProjectRecommendation.objects.count(), 1)
        record = ProjectRecommendation.objects.get(user=self.user)
        self.assertEqual(record.token_usage, 200)
        self.assertEqual(record.created_by, self.user)
        self.assertIsNotNone(record.updated_by)

    def test_generate_different_overview_creates_new_row(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 100)
        ):
            self.service.generate(
                user=self.user,
                domain="Software Development",
                domain_category="Technology",
                overview="Overview A",
            )
            self.service.generate(
                user=self.user,
                domain="Software Development",
                domain_category="Technology",
                overview="Overview B",
            )
        self.assertEqual(ProjectRecommendation.objects.count(), 2)

    def test_generate_requires_domain(self):
        with self.assertRaises(ProjectRecommendationAccessDeniedError):
            self.service.generate(
                user=self.user,
                domain="",
                domain_category="Technology",
            )

    def test_profile_type_maps_from_user_type(self):
        parent = User.objects.create_user(
            email="pr_parent@example.com",
            username="pr_parent",
            password="pass12345",
            user_type=User.Role.PARENT,
        )
        professional = User.objects.create_user(
            email="pr_pro@example.com",
            username="pr_pro",
            password="pass12345",
            user_type=User.Role.PROFESSIONAL,
        )
        self.assertEqual(
            ProjectRecommendationService._profile_type_for_user(self.user),
            ProjectRecommendation.ProfileType.STUDENT,
        )
        self.assertEqual(
            ProjectRecommendationService._profile_type_for_user(parent),
            ProjectRecommendation.ProfileType.PARENT,
        )
        self.assertEqual(
            ProjectRecommendationService._profile_type_for_user(professional),
            ProjectRecommendation.ProfileType.PROFESSIONAL,
        )

    def test_ai_not_configured_raises_configuration_error(self):
        with mock.patch.object(
            ProjectGenerator,
            "generate",
            side_effect=ProjectRecommendationConfigurationError("not configured"),
        ):
            with self.assertRaises(ProjectRecommendationConfigurationError):
                self.service.generate(
                    user=self.user,
                    domain="Software Development",
                    domain_category="Technology",
                )


class ProjectRecommendationAPITests(APITestCase):
    """POST with domain + domain_category dropdowns and an overview text field."""

    def setUp(self):
        self.url = reverse("api-project-recommendations")
        # superuser bypasses the subscription/token check in the test
        self.user = User.objects.create_superuser(
            email="pr_api@example.com",
            password="pass12345",
        )
        self.category = Domain.objects.create(
            domain_code="pr_api_category",
            domain_name="Technology",
        )
        self.domain = Domain.objects.create(
            domain_code="pr_api_domain",
            domain_name="Software Development",
            parent=self.category,
        )
        self.client.force_authenticate(user=self.user)

    def _post(self, **extra):
        body = {
            "domain_id": str(self.domain.id),
            "domain_category_id": str(self.category.id),
            "overview": "Build a career guidance web app for students",
        }
        body.update(extra)
        return self.client.post(self.url, body, format="json")

    def _create_record(self, user=None):
        return ProjectRecommendation.objects.create(
            user=user or self.user,
            profile_type=ProjectRecommendation.ProfileType.STUDENT,
            domain="Software Development",
            domain_category="Technology",
            overview="Build a career guidance web app for students",
            raw_ai_response=_make_payload().model_dump(),
            token_usage=321,
        )

    def test_post_generates_and_persists(self):
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(_make_payload(), 150)
        ) as mocked:
            resp = self._post()

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["success"])
        data = resp.data["data"]
        self.assertEqual(data["domain"], "Software Development")
        self.assertEqual(data["domain_category"], "Technology")
        self.assertNotIn("assessment_id", data)
        self.assertEqual(
            data["overview"], "Build a career guidance web app for students"
        )
        self.assertEqual(len(data["projects"]), 3)
        mocked.assert_called_once()
        # overview reaches the LLM prompt builder
        self.assertEqual(
            mocked.call_args.kwargs["overview"],
            "Build a career guidance web app for students",
        )

        record = ProjectRecommendation.objects.get(user=self.user)
        self.assertEqual(record.domain, "Software Development")
        self.assertEqual(record.domain_category, "Technology")
        self.assertEqual(
            record.overview, "Build a career guidance web app for students"
        )
        self.assertEqual(record.token_usage, 150)

    def test_post_repeated_input_upserts(self):
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(_make_payload(), 100)
        ):
            self._post()
            self._post()
        self.assertEqual(ProjectRecommendation.objects.count(), 1)

    def test_post_requires_domain_and_category(self):
        resp = self.client.post(self.url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("domain_id and domain_category_id", resp.data["message"])

        resp = self._post(domain_id="")
        self.assertEqual(resp.status_code, 400)

    def test_post_invalid_domain_ids(self):
        resp = self._post(domain_id="not-a-uuid")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("valid UUIDs", resp.data["message"])

        resp = self._post(domain_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid domain", resp.data["message"])

    def test_post_domain_not_in_category_rejected(self):
        other_category = Domain.objects.create(
            domain_code="pr_api_other",
            domain_name="Finance",
        )
        resp = self._post(domain_category_id=str(other_category.id))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("does not belong", resp.data["message"])

    def test_post_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self._post()
        self.assertEqual(resp.status_code, 401)

    def test_get_list_paginated(self):
        self._create_record()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get("results", {})
        self.assertTrue(results.get("success"))
        self.assertEqual(len(results["data"]), 1)

    def test_get_list_no_pagination(self):
        self._create_record()
        resp = self.client.get(self.url, {"no_pagination": 1})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("success"), True)
        self.assertEqual(len(resp.data["data"]), 1)

    def test_get_does_not_leak_other_users_data(self):
        other = User.objects.create_superuser(
            email="other_pr@example.com",
            password="pass12345",
        )
        self._create_record(user=other)
        resp = self.client.get(self.url)
        results = resp.data.get("results", {})
        self.assertEqual(len(results["data"]), 0)

    def test_post_ai_unavailable_returns_503(self):
        """AI not configured / disabled surfaces as a 503."""
        with mock.patch.object(
            ProjectGenerator,
            "generate",
            side_effect=ProjectRecommendationConfigurationError("not configured"),
        ):
            resp = self._post()
        self.assertEqual(resp.status_code, 503)
