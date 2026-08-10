"""
Unit tests for the LinkedIn Job Search integration.

Covers:
  - Successful search
  - Empty results
  - Invalid API key
  - Timeout
  - Rate limit
  - Serializer normalization
  - Cache hit / miss
  - Recommended jobs endpoint
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from assessment_career.models import CareerRecommendation, CareerSuggestion
from jobs.exceptions import (
    LinkedInJobAPIAuthError,
    LinkedInJobAPIRateLimitError,
    LinkedInJobAPITimeoutError,
    LinkedInJobServiceError,
)
from jobs.serializers import JobNormalizedSerializer, JobSearchQuerySerializer
from jobs.services import MAX_RETRIES, LinkedInJobService
from jobs.views import JobSearchAPIView, RecommendedJobsAPIView
from user.models import User

def _make_user(**kwargs) -> User:
    defaults = {
        "email": "test@example.com",
        "full_name": "Test User",
        "user_type": "student",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_assessment(user: User) -> tuple[CareerRecommendation, CareerSuggestion]:
    rec = CareerRecommendation.objects.create(
        user=user,
        profile_type="student",
    )
    suggestion = CareerSuggestion.objects.create(
        recommendation=rec,
        career_name="Python Developer",
        match_percentage=85,
        ai_insight="Great match for you.",
        why_this_career=["High demand", "Good salary"],
        required_skills=["Python", "Django"],
        required_education={
            "levels": [{"name": "Bachelor", "level_key": "graduation"}]
        },
        display_order=1,
    )
    return rec, suggestion


def _sample_raw_job(**overrides) -> dict:
    """
    Build a sample raw job in the format returned by the /active-jb endpoint.

    The /active-jb endpoint returns a flat list of job objects with fields
    like id, title, organization, locations (list), salary (object),
    employment_type (list), cities_derived (list), regions_derived (list),
    countries_derived (list), etc.
    """
    job = {
        "id": "2258428060",
        "title": "Python Developer",
        "organization": "Tech Corp",
        "organization_logo": "https://example.com/logo.png",
        "locations": [
            {
                "@type": "Place",
                "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Ahmedabad",
                    "addressRegion": "Gujarat",
                    "addressCountry": "India",
                },
            }
        ],
        "location_type": "remote",
        "cities_derived": ["Ahmedabad"],
        "regions_derived": ["Gujarat"],
        "countries_derived": ["India"],
        "employment_type": ["Full-time"],
        "seniority": "Mid",
        "salary": {
            "min_amount": 500000,
            "max_amount": 1200000,
            "currency": "INR",
        },
        "date_posted": "2026-07-14T10:00:00Z",
        "url": "https://linkedin.com/jobs/view/12345",
        "description": "We are looking for a Python Developer.",
        "skills": ["Python", "Django", "REST API"],
        "industry": "Information Technology",
        "experience_level": "Mid-Senior",
    }
    job.update(overrides)
    return job


def _mock_response(status_code=200, json_data=None):
    """Build a requests.Response-like mock with raise_for_status support."""
    from requests.exceptions import HTTPError

    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data or {}
    mock_resp.ok = status_code < 400

    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = HTTPError(
            f"{status_code} Client/Server Error"
        )
    else:
        mock_resp.raise_for_status.return_value = None

    return mock_resp

class JobSearchQuerySerializerTest(SimpleTestCase):
    def test_valid_minimal(self):
        serializer = JobSearchQuerySerializer(data={"title": "Python"})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["title"], "Python")
        self.assertEqual(serializer.validated_data["limit"], 10)
        self.assertEqual(serializer.validated_data["page"], 1)

    def test_valid_full(self):
        data = {
            "title": "Python Developer",
            "location": "Ahmedabad",
            "remote": True,
            "salary_min": 50000,
            "salary_max": 100000,
            "limit": 20,
            "page": 2,
        }
        serializer = JobSearchQuerySerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_salary_range(self):
        data = {"salary_min": 100000, "salary_max": 50000}
        serializer = JobSearchQuerySerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_limit_exceeds_max(self):
        data = {"limit": 100}
        serializer = JobSearchQuerySerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_empty_title_and_location(self):
        serializer = JobSearchQuerySerializer(data={})
        self.assertTrue(serializer.is_valid())


class JobNormalizedSerializerTest(SimpleTestCase):
    """
    Tests for ``JobNormalizedSerializer``.

    Note: the serializer expects data in the *standard Future4u format*
    (keys like ``id``, ``title``, ``company``), NOT the raw API format
    (``job_id``, ``job_title``, ``company_name``).  The raw→standard mapping
    is done by ``LinkedInJobService._map_raw_job()`` before the serializer
    is invoked.
    """

    def test_full_job_normalization(self):
        data = {
            "id": "12345",
            "title": "Python Developer",
            "company": "Tech Corp",
            "skills": ["Python", "Django", "REST API"],
            "source": "linkedin",
        }
        serializer = JobNormalizedSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        validated = serializer.validated_data
        self.assertEqual(validated["id"], "12345")
        self.assertEqual(validated["title"], "Python Developer")
        self.assertEqual(validated["company"], "Tech Corp")
        self.assertEqual(validated["skills"], ["Python", "Django", "REST API"])
        self.assertEqual(validated["source"], "linkedin")

    def test_missing_fields_default_to_empty(self):
        data = {"id": "1", "title": "Dev"}
        serializer = JobNormalizedSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        validated = serializer.validated_data
        self.assertEqual(validated["company"], "")
        self.assertEqual(validated["skills"], [])
        self.assertIsNone(validated["salary_min"])
        self.assertIsNone(validated["salary_max"])
        self.assertEqual(validated["source"], "linkedin")

    def test_null_skills_to_representation(self):
        """Skills=None → empty list in output representation."""
        data = {"id": "2", "title": "Dev", "skills": None}
        serializer = JobNormalizedSerializer(data=data)
        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        output = serializer.data
        self.assertEqual(output["skills"], [])

    def test_retains_skills_list_when_provided(self):
        """Provided skills list should remain as-is in representation."""
        data = {"id": "3", "title": "Engineer", "skills": ["Go", "K8s"]}
        serializer = JobNormalizedSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        output = serializer.data
        self.assertEqual(output["skills"], ["Go", "K8s"])

    def test_minimal_data_is_valid(self):
        """All fields have defaults so even an empty dict should be valid."""
        serializer = JobNormalizedSerializer(data={})
        self.assertTrue(serializer.is_valid())
        validated = serializer.validated_data
        self.assertEqual(validated["id"], "")
        self.assertEqual(validated["source"], "linkedin")

class LinkedInJobServiceTest(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.service = LinkedInJobService()
        self.mock_api_key = "test-key-123"
        self.mock_api_host = "test-host.p.rapidapi.com"

    def _apply_settings(self):
        """Patch settings attributes for the duration of a test."""
        return patch.multiple(
            settings,
            RAPIDAPI_KEY=self.mock_api_key,
            RAPIDAPI_HOST=self.mock_api_host,
        )

    @patch("jobs.services.requests.Session.get")
    def test_search_jobs_success(self, mock_get):
        raw_job = _sample_raw_job()
        api_response = {"data": [raw_job], "total": 1}
        mock_get.return_value = _mock_response(json_data=api_response)
        with self._apply_settings():
            result = self.service.search_jobs(
                {"title": "Python Developer", "location": "Ahmedabad"}
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["title"], "Python Developer")
        self.assertEqual(result["data"][0]["company"], "Tech Corp")

    @patch("jobs.services.requests.Session.get")
    def test_search_jobs_empty_results(self, mock_get):
        api_response = {"data": [], "total": 0}
        mock_get.return_value = _mock_response(json_data=api_response)
        with self._apply_settings():
            result = self.service.search_jobs({"title": "Nonexistent Job"})

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["data"], [])
        self.assertEqual(result["page"], 1)

    @patch("jobs.services.requests.Session.get")
    def test_cache_hit(self, mock_get):
        """A second identical search should use the cache, not call the API."""
        raw_job = _sample_raw_job()
        api_response = {"data": [raw_job], "total": 1}
        mock_get.return_value = _mock_response(json_data=api_response)

        with self._apply_settings():
            result1 = self.service.search_jobs(
                {"title": "Python Developer", "location": "Mumbai"}
            )
        self.assertTrue(result1["success"])
        self.assertEqual(mock_get.call_count, 1)

        with self._apply_settings():
            result2 = self.service.search_jobs(
                {"title": "Python Developer", "location": "Mumbai"}
            )
        self.assertTrue(result2["success"])
        self.assertEqual(mock_get.call_count, 1)  # Still 1 — cache hit
        self.assertEqual(result1, result2)

    @patch("jobs.services.requests.Session.get")
    def test_cache_miss_different_query(self, mock_get):
        """Different queries should each call the API."""
        mock_get.return_value = _mock_response(json_data={"data": [], "total": 0})

        with self._apply_settings():
            self.service.search_jobs({"title": "Python", "location": "Mumbai"})
            self.service.search_jobs({"title": "Java", "location": "Delhi"})

        self.assertEqual(mock_get.call_count, 2)

    @patch("jobs.services.requests.Session.get")
    def test_invalid_api_key(self, mock_get):
        mock_get.return_value = _mock_response(status_code=401)
        with self._apply_settings():
            with self.assertRaises(LinkedInJobAPIAuthError):
                self.service.search_jobs({"title": "Python"})

    @patch("jobs.services.requests.Session.get")
    def test_rate_limit_retry_then_fail(self, mock_get):
        """429 is retried, then raises after exhausting retries."""
        mock_get.return_value = _mock_response(status_code=429)
        with self._apply_settings():
            with self.assertRaises(LinkedInJobAPIRateLimitError):
                self.service.search_jobs({"title": "Python"})

        self.assertEqual(mock_get.call_count, 1 + MAX_RETRIES)

    @patch("jobs.services.requests.Session.get")
    def test_timeout(self, mock_get):
        from requests.exceptions import Timeout

        mock_get.side_effect = Timeout("Connection timed out")
        with self._apply_settings():
            with self.assertRaises(LinkedInJobAPITimeoutError):
                self.service.search_jobs({"title": "Python"})

    @patch("jobs.services.requests.Session.get")
    def test_connection_error(self, mock_get):
        from requests.exceptions import ConnectionError

        mock_get.side_effect = ConnectionError("Connection refused")
        with self._apply_settings():
            with self.assertRaises(LinkedInJobServiceError):
                self.service.search_jobs({"title": "Python"})

    @patch("jobs.services.requests.Session.get")
    def test_server_error_retry_then_fail(self, mock_get):
        """A 500 error should be retried, then raise after max retries."""
        mock_get.return_value = _mock_response(status_code=500)
        with self._apply_settings():
            with self.assertRaises(LinkedInJobServiceError):
                self.service.search_jobs({"title": "Python"})

        self.assertEqual(mock_get.call_count, 1 + MAX_RETRIES)

    @patch("jobs.services.requests.Session.get")
    def test_500_then_success_on_retry(self, mock_get):
        """Server error on first attempt, success on retry."""
        success_response = _mock_response(
            json_data={"data": [_sample_raw_job()], "total": 1}
        )
        mock_get.side_effect = [
            _mock_response(status_code=502),
            success_response,
        ]
        with self._apply_settings():
            result = self.service.search_jobs({"title": "Python"})

        self.assertTrue(result["success"])
        self.assertEqual(result["count"], 1)

    @override_settings(JOBS_LINKEDIN_SEARCH_ENABLED=False)
    def test_service_disabled(self):
        result = self.service.search_jobs({"title": "Python"})
        self.assertFalse(result["success"])
        self.assertIn("disabled", result["message"].lower())

    def test_missing_api_key(self):
        """No API key configured → LinkedInJobServiceError."""
        with override_settings(RAPIDAPI_KEY=""):
            with self.assertRaises(LinkedInJobServiceError):
                self.service.search_jobs({"title": "Python"})

    def test_cache_key_normalization(self):
        key1 = LinkedInJobService._build_cache_key("Python Developer", "Mumbai", 1)
        key2 = LinkedInJobService._build_cache_key("python developer", "mumbai", 1)
        self.assertEqual(key1, key2)



@override_settings(
    RAPIDAPI_KEY="test-key-123",
    RAPIDAPI_HOST="test-host.p.rapidapi.com",
)
class JobSearchAPIViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = _make_user()

    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()

    @patch("jobs.services.requests.Session.get")
    def test_search_endpoint_success(self, mock_get):
        raw_job = _sample_raw_job()
        api_response = {"data": [raw_job], "total": 1}
        mock_get.return_value = _mock_response(json_data=api_response)

        request = self.factory.get(
            "/api/jobs/search/?title=Python+Developer&location=Ahmedabad"
        )
        force_authenticate(request, user=self.user)
        response = JobSearchAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["data"][0]["title"], "Python Developer")

    def test_search_endpoint_unauthenticated(self):
        request = self.factory.get("/api/jobs/search/?title=Python")
        response = JobSearchAPIView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("jobs.services.requests.Session.get")
    def test_search_endpoint_empty(self, mock_get):
        api_response = {"data": [], "total": 0}
        mock_get.return_value = _mock_response(json_data=api_response)

        request = self.factory.get("/api/jobs/search/?title=zzznotexist")
        force_authenticate(request, user=self.user)
        response = JobSearchAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["count"], 0)

    def test_search_endpoint_invalid_params(self):
        request = self.factory.get("/api/jobs/search/?salary_min=100&salary_max=50")
        force_authenticate(request, user=self.user)
        response = JobSearchAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])


@override_settings(
    RAPIDAPI_KEY="test-key-123",
    RAPIDAPI_HOST="test-host.p.rapidapi.com",
)
class RecommendedJobsAPIViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = _make_user()

    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()

    def test_recommended_missing_assessment_id(self):
        request = self.factory.get("/api/jobs/recommended/")
        force_authenticate(request, user=self.user)
        response = RecommendedJobsAPIView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recommended_no_career_found(self):
        request = self.factory.get("/api/jobs/recommended/?assessment_id=9999")
        force_authenticate(request, user=self.user)
        response = RecommendedJobsAPIView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("jobs.services.requests.Session.get")
    def test_recommended_success(self, mock_get):
        _make_assessment(self.user)
        raw_job = _sample_raw_job()
        api_response = {"data": [raw_job], "total": 1}
        mock_get.return_value = _mock_response(json_data=api_response)

        rec = CareerRecommendation.objects.get(user=self.user)
        request = self.factory.get(f"/api/jobs/recommended/?assessment_id={rec.pk}")
        force_authenticate(request, user=self.user)
        response = RecommendedJobsAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["career_name"], "Python Developer")
        self.assertIn("jobs recommended", response.data["message"].lower())
