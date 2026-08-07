from __future__ import annotations

import logging
from uuid import UUID

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsIndividualUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from project_recommendation.exceptions import (
    ProjectRecommendationAccessDeniedError,
    ProjectRecommendationConfigurationError,
    ProjectRecommendationValidationError,
)
from project_recommendation.models import ProjectRecommendation
from project_recommendation.serializers import ProjectRecommendationSerializer
from project_recommendation.services.project_service import ProjectRecommendationService
from utils.pagination import Pagination
from utils.throttles import (
    ProjectRecommendationRateThrottle,
    ProjectRecommendationReadRateThrottle,
)
from utils.token_check import check_token_available, deduct_monthly_tokens

logger = logging.getLogger(__name__)

_service = ProjectRecommendationService()


class ProjectRecommendationAPIView(APIView):
    """
    POST /api/project-recommendations/

    Returns 3 portfolio project ideas for the domain dropdowns (master
    Domain table) plus an optional overview text. Fully standalone — not
    linked to any assessment or career recommendation.

    Projects are generated via the LLM (deducts tokens). The served
    response is persisted so saved projects remain visible via GET after
    the student logs back in.

    Request body:
    {
        "domain_id": "<uuid from /api/domains/dropdown/?parent_id=...>",
        "domain_category_id": "<uuid from /api/domains/dropdown/?root_only=1>",
        "overview": "I want to build a career guidance web app"
    }

    Response: domain, domain_category, overview, projects.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]

    def get_throttles(self):
        """Cheap DB reads get a generous limit; the LLM POST keeps 10/min."""
        if self.request.method == "GET":
            return [ProjectRecommendationReadRateThrottle()]
        return [ProjectRecommendationRateThrottle()]

    def get(self, request, *args, **kwargs):
        """
        GET /api/project-recommendations/

        Returns a paginated list of all saved recommendations for the
        logged-in user (or the full list with ?no_pagination=1). Data is
        read from the ProjectRecommendation table (persisted by POST).
        """
        queryset = ProjectRecommendation.objects.filter(
            user=request.user,
            deleted=False,
        ).order_by("-last_recommended_at", "-id")

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = ProjectRecommendationSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        paginator = Pagination()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = ProjectRecommendationSerializer(page, many=True)
            return paginator.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = ProjectRecommendationSerializer(queryset, many=True)
        return paginator.get_paginated_response(
            {"success": True, "data": serializer.data}
        )

    def post(self, request, *args, **kwargs):
        domain_id = request.data.get("domain_id")
        domain_category_id = request.data.get("domain_category_id")
        overview = str(request.data.get("overview", "") or "").strip()

        if not (domain_id and domain_category_id):
            return Response(
                {
                    "success": False,
                    "message": "domain_id and domain_category_id are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain, domain_category, error = self._resolve_domain_inputs(
            domain_id, domain_category_id
        )
        if error:
            return Response(
                {"success": False, "message": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Always regenerate: no cooldown/365-day cache on project
        # recommendations. Each POST runs the LLM, persists the result
        # and deducts tokens.
        try:
            check_token_available(request.user, "project_gen")
        except Exception as exc:
            logger.warning(
                "Token check failed for user=%s feature=project_gen: %s",
                request.user.id,
                exc,
            )
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        if not getattr(settings, "PROJECT_RECOMMENDATION_ENABLED", True):
            return Response(
                {
                    "success": False,
                    "message": "Project recommendations are currently disabled",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token_usage = 0
        try:
            data, token_usage = _service.generate(
                user=request.user,
                domain=domain,
                domain_category=domain_category,
                overview=overview,
            )
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=project_gen cost=%s err=%s",
                    request.user.id,
                    token_usage,
                    exc,
                )
            return Response(
                {"success": True, "data": data},
                status=status.HTTP_200_OK,
            )
        except ProjectRecommendationAccessDeniedError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProjectRecommendationConfigurationError as exc:
            logger.error("Project recommendation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI project recommendations are temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProjectRecommendationValidationError as exc:
            logger.warning(
                "Project recommendation validation failed error=%s details=%s",
                exc.error,
                exc.details,
            )
            return Response(
                {
                    "success": False,
                    "message": str(exc)
                    or "Unable to generate project recommendations. Please try again.",
                    "error": exc.error,
                    "details": exc.details,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.exception("Unexpected project recommendation error")
            return Response(
                {
                    "success": False,
                    "message": "Unable to generate project recommendations",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @staticmethod
    def _resolve_domain_inputs(domain_id, domain_category_id):
        """Resolve dropdown domain IDs to names and validate they belong together."""
        from domain.models import Domain

        try:
            domain_uuid = UUID(str(domain_id))
            category_uuid = UUID(str(domain_category_id))
        except (ValueError, TypeError):
            return None, None, "domain_id and domain_category_id must be valid UUIDs"

        domain_obj = Domain.objects.filter(
            id=domain_uuid, deleted=False
        ).first()
        category = Domain.objects.filter(id=category_uuid, deleted=False).first()
        if not domain_obj or not category:
            return None, None, "Invalid domain or domain category"

        if domain_obj.parent_id and str(domain_obj.parent_id) != str(category.id):
            return (
                None,
                None,
                "Selected domain does not belong to the selected domain category",
            )

        return domain_obj.domain_name, category.domain_name, None
