from rest_framework.routers import DefaultRouter

from assessment.studentassessment import (
    AssessmentResponseViewSet,
    NextQuestionViewSet,
    StudentAssessmentViewSet,
)

assessment_router = DefaultRouter()

# Student Assessment session endpoints
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
