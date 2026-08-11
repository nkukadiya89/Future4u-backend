from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from internship_generation.exceptions import (
    InternshipGenerationAccessDeniedError,
    InternshipGenerationConfigurationError,
    InternshipGenerationValidationError,
)
from internship_generation.serializers.internship_generation_input import (
    InternshipGenerationInputSerializer,
)
from internship_generation.services.internship_generation_service import (
    InternshipGenerationService,
)
from user.permissions import HasPerm
from utils.throttles import InternshipGenerationRateThrottle
from utils.token_check import OrganizationTokenChargeError, check_token_available

logger = logging.getLogger(__name__)


class InternshipGenerationAPIView(APIView):
    """
    POST /api/ai-internship-generation/
    Generates AI internship fields from user-provided Post Internship form details.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, HasPerm]
    required_permission = "internship_generation.generate_internship"
    throttle_classes = [InternshipGenerationRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = InternshipGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check_token_available(request.user, "internship_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            data, _ = InternshipGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
                feature_code="internship_gen",
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except OrganizationTokenChargeError as exc:
            logger.error(
                "Organization token charge failed user=%s feature=internship_gen err=%s",
                request.user.id,
                exc,
            )
            return Response(
                {"success": False, "message": "Unable to process token accounting"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except InternshipGenerationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Internship generation is only available for "
                        "institute and corporate accounts"
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except InternshipGenerationConfigurationError as exc:
            logger.error("Internship generation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI internship generation is temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except InternshipGenerationValidationError as exc:
            logger.warning(
                "Internship generation validation failed error=%s details=%s",
                exc.error,
                exc.details,
            )
            return Response(
                {
                    "success": False,
                    "message": str(exc)
                    or "Unable to generate internship details. Please try again.",
                    "error": exc.error,
                    "details": exc.details,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception:
            logger.exception("Unexpected internship generation error")
            return Response(
                {"success": False, "message": "Unable to generate internship details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
