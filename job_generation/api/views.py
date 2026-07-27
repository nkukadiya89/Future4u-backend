from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsAdminOrProvider
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from internship_job.models import Job
from internship_job.serializers import JobSerializer

from job_generation.exceptions import (
    JobGenerationAccessDeniedError,
    JobGenerationConfigurationError,
    JobGenerationValidationError,
)
from job_generation.serializers.job_generation_input import JobGenerationInputSerializer
from job_generation.services.job_generation_service import JobGenerationService
from utils.throttles import JobGenerationRateThrottle
from utils.token_check import check_token_available, deduct_monthly_tokens

logger = logging.getLogger(__name__)


class JobGenerationAPIView(APIView):
    """
    POST /api/ai-job-generation/
    Generates AI job posting fields from user-provided inputs and returns
    the result. Use POST /job/ to save the returned data to the database.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    throttle_classes = [JobGenerationRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = JobGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check token availability before AI call
        try:
            check_token_available(request.user, "job_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        token_usage = 0
        try:
            data, token_usage = JobGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
            )
            # Deduct actual LLM token usage after successful AI call
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=job_gen cost=%s err=%s",
                    request.user.id, token_usage, exc,
                )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

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
                    "message": str(exc) or "Unable to generate job details. Please try again.",
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


class JobGenerationSaveView(APIView):
    """
    POST /api/ai-job-generation/save/
    Generates AI job fields AND saves the complete Job to the database.
    Sales manager flow: provide inputs → AI generates → job saved in one call.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    throttle_classes = [JobGenerationRateThrottle]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = JobGenerationInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check token availability before AI call
        try:
            check_token_available(request.user, "job_gen")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        token_usage = 0
        try:
            generated_data, token_usage = JobGenerationService().generate(
                user=request.user,
                validated_input=serializer.validated_data,
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
                    "message": str(exc) or "Unable to generate job details. Please try again.",
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

        # Extract M2M education_tags PKs before creating the Job
        education_tags_pks = generated_data.pop("education_tags", [])

        # Remove non-DB fields (display-only or not a Job model field)
        generated_data.pop("education_tags_meta", None)
        generated_data.pop("corporate_name", None)
        generated_data.pop("country_name", None)
        generated_data.pop("state_name", None)
        generated_data.pop("city_name", None)
        generated_data.pop("application_deadline", None)

        # If choice fields are empty strings, pop them so model defaults apply
        for field in ("job_type", "experience_level", "mode"):
            if generated_data.get(field) in (None, ""):
                generated_data.pop(field, None)

        # Convert FK PK values to *_id format for Django ORM create()
        fk_aliases = {
            "corporate": "corporate_id",
            "country": "country_id",
            "state": "state_id",
            "city": "city_id",
        }
        for field, alias in fk_aliases.items():
            fk_value = generated_data.pop(field, None)
            if fk_value is not None:
                generated_data[alias] = fk_value

        save_mode = request.data.get("save_mode", "draft")
        if save_mode not in ("draft", "publish"):
            save_mode = "draft"
        
        # Deduct actual LLM token usage after successful AI call
        try:
            deduct_monthly_tokens(request.user, token_usage)
        except Exception as exc:
            logger.error(
                "TOKEN_RECONCILE user=%s feature=job_gen_save cost=%s err=%s",
                request.user.id, token_usage, exc,
            )

        job = Job.objects.create(
            **generated_data,
            provider=request.user,
            created_by=request.user,
            created_at=timezone.now(),
            status="active" if save_mode == "publish" else "draft",
        )

        if education_tags_pks:
            job.education_tags.set(education_tags_pks)

        job_serializer = JobSerializer(job, context={"request": request})
        
        message = "Job saved as draft" if save_mode == "draft" else "Job posted successfully"
        
        return Response(
            {
                "success": True,
                "message": message,
                "data": job_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
