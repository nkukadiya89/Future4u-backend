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
from utils.throttles import InternshipGenerationRateThrottle
from utils.token_check import check_token_available, deduct_monthly_tokens

logger = logging.getLogger(__name__)


class InternshipGenerationAPIView(APIView):
    """
    POST /api/ai-internship-generation/
    Generates AI internship fields from user-provided Post Internship form details.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [InternshipGenerationRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = InternshipGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check token availability before AI call
        try:
            check_token_available(request.user, "internship_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            data, token_usage = InternshipGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
            )
            # Deduct actual LLM token usage after successful AI call
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=internship_gen cost=%s err=%s",
                    request.user.id, token_usage, exc,
                )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except InternshipGenerationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Internship generation is only available for "
                        "corporate and employer accounts"
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
