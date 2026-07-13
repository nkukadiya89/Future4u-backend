from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from course_generation.exceptions import (
    CourseGenerationAccessDeniedError,
    CourseGenerationConfigurationError,
    CourseGenerationValidationError,
)
from course_generation.serializers.course_generation_input import (
    CourseGenerationInputSerializer,
)
from course_generation.services.course_generation_service import CourseGenerationService
from utils.throttles import CourseGenerationRateThrottle
from utils.token_check import check_and_deduct_token

logger = logging.getLogger(__name__)


class CourseGenerationAPIView(APIView):
    """
    POST /api/ai-course-generation/
    Generates AI course fields from user-provided Add Course form details.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [CourseGenerationRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = CourseGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check token availability before AI call
        try:
            check_and_deduct_token(request.user, "course_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            data = CourseGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
            )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        except CourseGenerationAccessDeniedError:
            return Response(
                {
                    "success": False,
                    "message": "Course generation is only available for institute accounts",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        except CourseGenerationConfigurationError as exc:
            logger.error("Course generation configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI course generation is temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except CourseGenerationValidationError as exc:
            logger.warning(
                "Course generation validation failed error=%s details=%s",
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
            logger.exception("Unexpected course generation error")
            return Response(
                {"success": False, "message": "Unable to generate course details"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
