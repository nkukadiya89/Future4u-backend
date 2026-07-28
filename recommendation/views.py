import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from user.permissions import IsIndividualUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from recommendation.engine.dispatch import (
    resolve_chat_service,
    resolve_recommendation_service,
)
from recommendation.exceptions import (
    AIConfigurationError,
    AIGenerationError,
    AssessmentAccessDeniedError,
    AssessmentNotFoundError,
    AssessmentNotReadyError,
)
from utils.throttles import AIChatRateThrottle, RecommendationRateThrottle
from utils.token_check import check_token_available, deduct_monthly_tokens
from assessment.models import ParentAssessment, ProfessionalAssessment, StudentAssessment

logger = logging.getLogger(__name__)


AssessmentModel = StudentAssessment | ParentAssessment | ProfessionalAssessment


def _resolve_assessment_type(
    user, assessment_id: int
) -> tuple[AssessmentModel | None, str | None]:

    checks: list[tuple[type[AssessmentModel], str]] = [
        (StudentAssessment, "student"),
        (ParentAssessment, "parent"),
        (ProfessionalAssessment, "professional"),
    ]
    for Model, ptype in checks:
        try:
            assessment = Model.objects.get(
                id=assessment_id, user=user, deleted=False
            )
            return assessment, ptype
        except Model.DoesNotExist:
            continue
    return None, None


class RecommendationAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]
    throttle_classes = [RecommendationRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        assessment, determined_type = _resolve_assessment_type(
            request.user, assessment_id
        )
        if not assessment:
            return Response(
                {"success": False, "message": "Assessment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not assessment.is_completed:
            return Response(
                {
                    "success": False,
                    "message": "Please complete your profile assessment first to get career recommendations.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile_type = (
                request.query_params.get("profile_type") or determined_type
            )
            result = resolve_recommendation_service(
                assessment_id, profile_type=profile_type
            )

            # Check minimum token balance (3000) before AI call
            try:
                check_token_available(request.user, "recommendation")
            except Exception as exc:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            token_usage = 0
            data, token_usage = result.service.generate(
                assessment_id=assessment_id,
                user=request.user,
            )
            # Deduct actual LLM token usage after successful AI call
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=recommendation cost=%s err=%s",
                    request.user.id, token_usage, exc,
                )

            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Assessment not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Assessment access denied"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AssessmentNotReadyError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AIConfigurationError as exc:
            logger.error("AI configuration error: %s", exc)
            return Response(
                {
                    "success": False,
                    "message": "AI recommendations are temporarily unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI generation failed")
            return Response(
                {
                    "success": False,
                    "message": "Unable to generate recommendations right now. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI recommendation error")
            return Response(
                {"success": False, "message": "Unable to generate AI recommendations"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RecommendationChatAPIView(APIView):
    """
    Unified chat endpoint (GET = context, POST = ask).

    Auto-detects the assessment type from the assessment_id and dispatches to
    the correct chat service implementation.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsIndividualUser]
    throttle_classes = [AIChatRateThrottle]

    def get(self, request, assessment_id, *args, **kwargs):
        try:
            assessment, determined_type = _resolve_assessment_type(
                request.user, assessment_id
            )
            if not assessment:
                return Response(
                    {"success": False, "message": "Assessment not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            profile_type = (
                request.query_params.get("profile_type") or determined_type
            )
            result = resolve_chat_service(assessment_id, profile_type=profile_type)
            data = result.service.context(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.query_params.get("suggestion_id"),
            )
            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Recommendation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Invalid career suggestion"},
                status=status.HTTP_403_FORBIDDEN,
            )

    def post(self, request, assessment_id, *args, **kwargs):
        # Check token availability before AI call
        try:
            check_token_available(request.user, "ai_chat")
        except Exception as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        try:
            assessment, determined_type = _resolve_assessment_type(
                request.user, assessment_id
            )
            if not assessment:
                return Response(
                    {"success": False, "message": "Assessment not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            profile_type = (
                request.query_params.get("profile_type") or determined_type
            )
            result = resolve_chat_service(assessment_id, profile_type=profile_type)
            data = result.service.ask(
                user=request.user,
                assessment_id=assessment_id,
                suggestion_id=request.data.get("suggestion_id"),
                question=request.data.get("message"),
            )
            # Deduct actual LLM token usage after successful AI call
            token_usage = data.pop("_token_usage", 0)
            try:
                deduct_monthly_tokens(request.user, token_usage)
            except Exception as exc:
                logger.error(
                    "TOKEN_RECONCILE user=%s feature=ai_chat cost=%s err=%s",
                    request.user.id, token_usage, exc,
                )

            return Response(
                {
                    "success": True,
                    "profile_type": result.profile_type,
                    "data": data,
                },
                status=status.HTTP_200_OK,
            )
        except (TypeError, ValueError) as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AssessmentNotFoundError:
            return Response(
                {"success": False, "message": "Recommendation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AssessmentAccessDeniedError:
            return Response(
                {"success": False, "message": "Invalid career suggestion"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AIConfigurationError as exc:
            logger.error("AI chat configuration error: %s", exc)
            return Response(
                {"success": False, "message": "AI chat is temporarily unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIGenerationError as exc:
            logger.exception("AI chat failed")
            return Response(
                {
                    "success": False,
                    "message": "Unable to answer right now. Please try again.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.exception("Unexpected AI chat error")
            return Response(
                {"success": False, "message": "Unable to answer right now"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
