from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from job_generation.exceptions import (
    JobGenerationAccessDeniedError,
    JobGenerationConfigurationError,
    JobGenerationValidationError,
)
from job_generation.serializers.job_generation_input import JobGenerationInputSerializer
from job_generation.services.job_generation_service import JobGenerationService
from user.permissions import HasPerm
from utils.throttles import JobGenerationRateThrottle
from utils.token_check import OrganizationTokenChargeError, check_token_available

logger = logging.getLogger(__name__)


class JobGenerationAPIView(APIView):
    """
    POST /api/ai-job-generation/
    Generates AI job posting fields from user-provided inputs and returns
    the result. Use POST /job/ to save the returned data to the database.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    required_permission = "job_generation.generate_job"
    throttle_classes = [JobGenerationRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = JobGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check_token_available(request.user, "job_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            data, _ = JobGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
                feature_code="job_gen",
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

        except OrganizationTokenChargeError as exc:
            logger.error(
                "Organization token charge failed user=%s feature=job_gen err=%s",
                request.user.id,
                exc,
            )
            return Response(
                {"success": False, "message": "Unable to process token accounting"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except JobGenerationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": "Job generation is only available for corporate accounts",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except JobGenerationConfigurationError as exc:
            logger.error("Job generation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI job generation is temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except JobGenerationValidationError as exc:
            logger.warning(
                "Job generation validation failed error=%s details=%s",
                exc.error,
                exc.details,
            )
            return Response(
                {
                    "success": False,
                    "message": str(exc)
                    or "Unable to generate job details. Please try again.",
                    "error": exc.error,
                    "details": exc.details,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.exception("Unexpected job generation error")
            return Response(
                {"success": False, "message": "Unable to generate job details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
