from rest_framework.routers import DefaultRouter

from assessment.views import (
    ApiAssessmentQuestionsViewSet,
    ApiAssessmentSubmitViewSet,
    ApiAssessmentSummaryViewSet,
    QuestionViewSet,
    UserResponseViewSet,
)
from assessment.studentassessment import (
    AssessmentResponseViewSet,
    NextQuestionViewSet,
    StudentAssessmentViewSet,
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

# NEW: Student Assessment session endpoints (step-by-step flow)
assessment_router.register(
    "api/student/assessments",
    StudentAssessmentViewSet,
    basename="student_assessment",
)
assessment_router.register(
    "api/questions/next",
    NextQuestionViewSet,
    basename="next_question",
)
assessment_router.register(
    "api/responses",
    AssessmentResponseViewSet,
    basename="assessment_responses_stored",
)
