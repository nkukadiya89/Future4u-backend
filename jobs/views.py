"""
DRF views for the LinkedIn Job Search integration.

Endpoints:
  GET /api/jobs/search/      – search real jobs by keyword, location, filters
  GET /api/jobs/recommended/ – load AI career recommendation → search matching jobs
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment_career.models import CareerSuggestion
from jobs.exceptions import LinkedInJobAPIAuthError, LinkedInJobAPIRateLimitError, LinkedInJobAPIError, LinkedInJobAPITimeoutError, LinkedInJobServiceError
from jobs.serializers import JobSearchQuerySerializer
from jobs.services import LinkedInJobService
from utils.throttles import PerUserBurstRateThrottle

logger = logging.getLogger(__name__)


class JobSearchAPIView(APIView):
    """
    GET /api/jobs/search/

    Search for real jobs from LinkedIn via the external API.

    Query parameters
    ----------------
    title            : str   – job title keyword(s)
    location         : str   – city, state, or country
    country          : str
    state            : str
    city             : str
    experience_level : str
    employment_type  : str
    remote           : bool  – filter remote jobs
    hybrid           : bool  – filter hybrid jobs
    salary_min       : int
    salary_max       : int
    company          : str
    posted_within    : str   – e.g. "24h", "week", "month"
    limit            : int   – results per page (max 50, default 10)
    page             : int   – page number (default 1)

    Example
    -------
    GET /api/jobs/search/?title=Python%20Developer&location=Ahmedabad&page=1
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [PerUserBurstRateThrottle]

    def get(self, request, *args, **kwargs):
        # Validate input
        query_serializer = JobSearchQuerySerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Invalid search parameters.",
                    "errors": query_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated = query_serializer.validated_data

        service = LinkedInJobService()

        try:
            result = service.search_jobs(params=validated)
        except LinkedInJobAPIAuthError as exc:
            logger.error("Job search auth error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch jobs. Authentication failed.",
                    "error_code": "EXTERNAL_API_AUTH_ERROR",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except LinkedInJobAPIRateLimitError as exc:
            logger.warning("Job search rate limit: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch jobs. Rate limit exceeded. Please try again later.",
                    "error_code": "EXTERNAL_API_RATE_LIMIT",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LinkedInJobAPITimeoutError as exc:
            logger.warning("Job search timeout: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch jobs. Request timed out. Please try again.",
                    "error_code": "EXTERNAL_API_TIMEOUT",
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except LinkedInJobAPIError as exc:
            logger.error("Job search API error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch jobs.",
                    "error_code": "EXTERNAL_API_ERROR",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except LinkedInJobServiceError as exc:
            logger.error("Job search service error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                    "error_code": "SERVICE_CONFIG_ERROR",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected error during job search")
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred. Please try again.",
                    "error_code": "INTERNAL_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=status.HTTP_200_OK)


class RecommendedJobsAPIView(APIView):
    """
    GET /api/jobs/recommended/

    Load the user's AI career recommendation and search matching LinkedIn jobs.

    Query parameters
    ----------------
    assessment_id : int  (required) – the assessment whose top career to use

    The endpoint takes the top career name from the recommendation and
    searches LinkedIn jobs matching that career title in the user's city/state.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [PerUserBurstRateThrottle]

    def get(self, request, *args, **kwargs):
        assessment_id = request.query_params.get("assessment_id")
        if not assessment_id:
            return Response(
                {
                    "success": False,
                    "message": "assessment_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            assessment_id = int(assessment_id)
        except (TypeError, ValueError):
            return Response(
                {
                    "success": False,
                    "message": "assessment_id must be a valid integer.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the top career suggestion for this user
        try:
            career = (
                CareerSuggestion.objects.filter(
                    recommendation__user=request.user,
                    recommendation__id=assessment_id,
                    recommendation__deleted=False,
                    deleted=False,
                )
                .select_related("recommendation")
                .order_by("-match_percentage", "display_order")
                .first()
            )
        except Exception as exc:
            logger.exception("Error fetching career recommendation")
            return Response(
                {
                    "success": False,
                    "message": "Unable to load career recommendation.",
                    "error_code": "DATABASE_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not career:
            return Response(
                {
                    "success": False,
                    "message": "No career recommendation found for this assessment.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        career_name = career.career_name or ""
        if not career_name:
            return Response(
                {
                    "success": False,
                    "message": "The recommended career has no name.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build search params based on the career name and user location
        search_params = {
            "title": career_name,
            "limit": 20,
        }

        # Try to infer location from the user's profile
        user = request.user
        location_parts = []

        if hasattr(user, "city") and user.city:
            location_parts.append(user.city.name)
        if hasattr(user, "state") and user.state:
            location_parts.append(user.state.name)
        if hasattr(user, "country") and user.country:
            location_parts.append(user.country.name)

        if location_parts:
            search_params["location"] = ", ".join(location_parts)

        service = LinkedInJobService()

        try:
            result = service.search_jobs(params=search_params)
        except (LinkedInJobAPIAuthError, LinkedInJobAPIError, LinkedInJobAPITimeoutError) as exc:
            logger.error("Recommended jobs API error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch recommended jobs.",
                    "error_code": "EXTERNAL_API_ERROR",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except LinkedInJobAPIRateLimitError as exc:
            logger.warning("Recommended jobs rate limit: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "Unable to fetch recommended jobs. Rate limit exceeded.",
                    "error_code": "EXTERNAL_API_RATE_LIMIT",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except LinkedInJobServiceError as exc:
            logger.error("Recommended jobs service error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                    "error_code": "SERVICE_CONFIG_ERROR",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected error during recommended jobs")
            return Response(
                {
                    "success": False,
                    "message": "An unexpected error occurred.",
                    "error_code": "INTERNAL_ERROR",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Add the career context to the response
        result["career_name"] = career_name
        result["career_id"] = career.pk
        result["assessment_id"] = career.recommendation_id
        result["message"] = f"Jobs recommended for {career_name}."

        return Response(result, status=status.HTTP_200_OK)
