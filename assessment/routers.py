from rest_framework.routers import DefaultRouter

from assessment.views import (
    ApiAssessmentQuestionsViewSet,
    ApiAssessmentSubmitViewSet,
    ApiAssessmentSummaryViewSet,
    QuestionViewSet,
    UserResponseViewSet,
)

assessment_router = DefaultRouter()
assessment_router.register(
    "assessment/questions", QuestionViewSet, basename="assessment_questions"
)
assessment_router.register(
    "assessment/responses", UserResponseViewSet, basename="assessment_responses"
)
assessment_router.register(
    "api/assessment/questions",
    ApiAssessmentQuestionsViewSet,
    basename="api_assessment_questions",
)
assessment_router.register(
    "api/assessment/submit",
    ApiAssessmentSubmitViewSet,
    basename="api_assessment_submit",
)
assessment_router.register(
    "api/assessment/summary",
    ApiAssessmentSummaryViewSet,
    basename="api_assessment_summary",
)
