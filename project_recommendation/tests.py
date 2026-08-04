from __future__ import annotations

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from assessment.models import (
    ParentAssessment,
    ProfessionalAssessment,
    StudentAssessment,
)
from domain.models import Domain
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


class ProjectRecommendationPersistenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pr_tester@example.com",
            username="pr_tester",
            password="pass12345",
        )
        self.domain = Domain.objects.create(
            domain_code="pr_domain",
            domain_name="Software Development",
        )
        self.category = Domain.objects.create(
            domain_code="pr_category",
            domain_name="Technology",
        )
        self.assessment = StudentAssessment.objects.create(
            user=self.user,
            domain=self.domain,
            domain_category=self.category,
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
                assessment_id=self.assessment.id,
            )

        self.assertEqual(token_usage, 1234)
        self.assertEqual(response["domain"], "Software Development")
        self.assertEqual(response["domain_category"], "Technology")
        self.assertEqual(response["assessment_id"], self.assessment.id)
        self.assertEqual(response["education_level"], "")
        self.assertEqual(len(response["projects"]), 3)

        record = ProjectRecommendation.objects.get(
            student_assessment=self.assessment
        )
        self.assertEqual(record.profile_type, ProjectRecommendation.ProfileType.STUDENT)
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.domain, "Software Development")
        self.assertEqual(record.domain_category, "Technology")
        self.assertEqual(record.education_level, "")
        self.assertEqual(record.token_usage, 1234)
        self.assertIsNotNone(record.last_recommended_at)
        self.assertEqual(record.created_by, self.user)
        # Full AI payload stored verbatim
        self.assertEqual(
            record.raw_ai_response,
            payload.model_dump(),
        )
        self.assertEqual(
            len(record.raw_ai_response["projects"]),
            3,
        )

    def test_generate_upserts_instead_of_duplicating(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator,
            "generate",
            return_value=(payload, 100),
        ):
            self.service.generate(user=self.user, assessment_id=self.assessment.id)

        with mock.patch.object(
            ProjectGenerator,
            "generate",
            return_value=(payload, 200),
        ):
            self.service.generate(user=self.user, assessment_id=self.assessment.id)

        self.assertEqual(ProjectRecommendation.objects.count(), 1)
        record = ProjectRecommendation.objects.get(
            student_assessment=self.assessment
        )
        self.assertEqual(record.token_usage, 200)
        self.assertEqual(record.created_by, self.user)
        self.assertIsNotNone(record.updated_by)

    def test_relation_kwargs_for_each_profile_type(self):
        parent = ParentAssessment.objects.create(user=self.user)
        professional = ProfessionalAssessment.objects.create(user=self.user)

        # Student assessment maps to the student FK
        kwargs = self.service._assessment_relation_kwargs(self.assessment)
        self.assertEqual(
            kwargs["profile_type"], ProjectRecommendation.ProfileType.STUDENT
        )
        self.assertIs(kwargs["student_assessment"], self.assessment)
        self.assertNotIn("parent_assessment", kwargs)
        self.assertNotIn("professional_assessment", kwargs)

        # Parent assessment maps to the parent FK
        kwargs = self.service._assessment_relation_kwargs(parent)
        self.assertEqual(
            kwargs["profile_type"], ProjectRecommendation.ProfileType.PARENT
        )
        self.assertIs(kwargs["parent_assessment"], parent)
        self.assertNotIn("student_assessment", kwargs)
        self.assertNotIn("professional_assessment", kwargs)

        # Professional assessment maps to the professional FK
        kwargs = self.service._assessment_relation_kwargs(professional)
        self.assertEqual(
            kwargs["profile_type"], ProjectRecommendation.ProfileType.PROFESSIONAL
        )
        self.assertIs(kwargs["professional_assessment"], professional)
        self.assertNotIn("student_assessment", kwargs)
        self.assertNotIn("parent_assessment", kwargs)


class ProjectRecommendationAPITests(APITestCase):
    """GET /api/project-recommendations/ — read saved recommendations back."""

    def setUp(self):
        self.url = reverse("api-project-recommendations")
        self.user = User.objects.create_user(
            email="pr_api@example.com",
            username="pr_api",
            password="pass12345",
            user_type=User.Role.STUDENT,
            is_active=True,
            status="active",
        )
        self.domain = Domain.objects.create(
            domain_code="pr_api_domain",
            domain_name="Software Development",
        )
        self.category = Domain.objects.create(
            domain_code="pr_api_category",
            domain_name="Technology",
        )
        self.assessment = StudentAssessment.objects.create(
            user=self.user,
            domain=self.domain,
            domain_category=self.category,
        )
        self.record = ProjectRecommendation.objects.create(
            user=self.user,
            profile_type=ProjectRecommendation.ProfileType.STUDENT,
            student_assessment=self.assessment,
            domain="Software Development",
            domain_category="Technology",
            education_level="12th Grade",
            raw_ai_response=_make_payload().model_dump(),
            token_usage=321,
        )
        self.client.force_authenticate(user=self.user)

    def test_get_by_assessment_id(self):
        response = self.client.get(self.url, {"assessment_id": self.assessment.id})
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["assessment_id"], self.assessment.id)
        self.assertEqual(data["profile_type"], "student")
        self.assertEqual(data["domain"], "Software Development")
        self.assertEqual(data["domain_category"], "Technology")
        self.assertEqual(data["education_level"], "12th Grade")
        self.assertEqual(data["token_usage"], 321)
        self.assertEqual(len(data["projects"]), 3)
        self.assertEqual(data["projects"][0]["project_name"], "AI Portfolio Builder 0")

    def test_get_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url, {"assessment_id": self.assessment.id})
        self.assertEqual(response.status_code, 401)

    def test_get_by_assessment_id_not_found(self):
        response = self.client.get(self.url, {"assessment_id": 999999})
        self.assertEqual(response.status_code, 404)

    def test_get_invalid_assessment_id(self):
        response = self.client.get(self.url, {"assessment_id": "abc"})
        self.assertEqual(response.status_code, 400)

    def test_get_list_paginated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        results = response.data.get("results", {})
        self.assertTrue(results.get("success"))
        self.assertEqual(len(results["data"]), 1)

    def test_get_list_no_pagination(self):
        response = self.client.get(self.url, {"no_pagination": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("success"), True)
        self.assertEqual(len(response.data["data"]), 1)

    def test_get_does_not_leak_other_users_data(self):
        other = User.objects.create_user(
            email="other_api@example.com",
            username="other_api",
            password="pass12345",
            user_type=User.Role.STUDENT,
            is_active=True,
            status="active",
        )
        other_assessment = StudentAssessment.objects.create(
            user=other,
            domain=self.domain,
            domain_category=self.category,
        )
        ProjectRecommendation.objects.create(
            user=other,
            profile_type=ProjectRecommendation.ProfileType.STUDENT,
            student_assessment=other_assessment,
            domain="Other Domain",
            domain_category="Other",
            raw_ai_response=_make_payload().model_dump(),
        )

        # by assessment_id -> 404 (not owned)
        response = self.client.get(self.url, {"assessment_id": other_assessment.id})
        self.assertEqual(response.status_code, 404)

        # list -> only own records
        response = self.client.get(self.url)
        results = response.data.get("results", {})
        self.assertEqual(len(results["data"]), 1)


class ProjectRecommendationGenerateOnceTests(APITestCase):
    """POST generates once per assessment; later clicks reuse the saved result."""

    def setUp(self):
        self.url = reverse("api-project-recommendations")
        # superuser bypasses the subscription/token check in the test
        self.user = User.objects.create_superuser(
            email="pr_once@example.com",
            password="pass12345",
        )
        self.domain = Domain.objects.create(
            domain_code="pr_once_domain",
            domain_name="Software Development",
        )
        self.assessment = StudentAssessment.objects.create(
            user=self.user,
            domain=self.domain,
            domain_category=self.domain,
        )
        self.client.force_authenticate(user=self.user)

    def test_second_post_reuses_saved_result_without_ai(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 100)
        ) as mocked:
            # first click -> generates
            resp1 = self.client.post(
                self.url, {"assessment_id": self.assessment.id}, format="json"
            )
            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(len(resp1.data["data"]["projects"]), 3)

            # second click -> returns the saved result, AI NOT called again
            resp2 = self.client.post(
                self.url, {"assessment_id": self.assessment.id}, format="json"
            )
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(resp2.data["success"], True)
            self.assertEqual(
                resp2.data["data"]["assessment_id"], self.assessment.id
            )
            self.assertEqual(len(resp2.data["data"]["projects"]), 3)

        # still exactly one row (no duplicates)
        self.assertEqual(ProjectRecommendation.objects.count(), 1)

    def test_new_assessment_after_saved_one_still_generates(self):
        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 100)
        ) as mocked:
            # first assessment generates once
            self.client.post(
                self.url, {"assessment_id": self.assessment.id}, format="json"
            )
            self.assertEqual(mocked.call_count, 1)

            # a DIFFERENT assessment still generates (fresh AI call)
            other = StudentAssessment.objects.create(
                user=self.user,
                domain=self.domain,
                domain_category=self.domain,
            )
            resp = self.client.post(
                self.url, {"assessment_id": other.id}, format="json"
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(mocked.call_count, 2)
        self.assertEqual(ProjectRecommendation.objects.count(), 2)

    def test_regenerates_after_365_day_cycle(self):
        # saved record dated 366 days ago (cycle expired, counted from own date)
        record = ProjectRecommendation.objects.create(
            user=self.user,
            profile_type=ProjectRecommendation.ProfileType.STUDENT,
            student_assessment=self.assessment,
            domain="Software Development",
            domain_category="Technology",
            raw_ai_response=_make_payload().model_dump(),
            token_usage=50,
        )
        record.last_recommended_at = timezone.now() - timedelta(days=366)
        record.save(update_fields=["last_recommended_at"])

        payload = _make_payload()
        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(payload, 200)
        ) as mocked:
            resp = self.client.post(
                self.url, {"assessment_id": self.assessment.id}, format="json"
            )
            self.assertEqual(resp.status_code, 200)
            # cycle expired -> fresh AI call
            self.assertEqual(mocked.call_count, 1)

        # same row upserted with the new result and timestamp
        record.refresh_from_db()
        self.assertEqual(record.token_usage, 200)
        self.assertGreater(
            record.last_recommended_at, timezone.now() - timedelta(days=1)
        )
        self.assertEqual(ProjectRecommendation.objects.count(), 1)

    def test_reuses_saved_within_365_day_cycle(self):
        # saved record dated 300 days ago (still within cycle, own date)
        record = ProjectRecommendation.objects.create(
            user=self.user,
            profile_type=ProjectRecommendation.ProfileType.STUDENT,
            student_assessment=self.assessment,
            domain="Software Development",
            domain_category="Technology",
            raw_ai_response=_make_payload().model_dump(),
            token_usage=50,
        )
        record.last_recommended_at = timezone.now() - timedelta(days=300)
        record.save(update_fields=["last_recommended_at"])

        with mock.patch.object(
            ProjectGenerator, "generate", return_value=(_make_payload(), 200)
        ) as mocked:
            resp = self.client.post(
                self.url, {"assessment_id": self.assessment.id}, format="json"
            )
            self.assertEqual(resp.status_code, 200)
            # within cycle -> NO AI call, saved data returned
            self.assertEqual(mocked.call_count, 0)
            self.assertEqual(len(resp.data["data"]["projects"]), 3)

        record.refresh_from_db()
        self.assertEqual(record.token_usage, 50)  # untouched
