from rest_framework.routers import DefaultRouter

from assessment.parentassessment import ParentAssessmentViewSet
from assessment.professionalassessment import ProfessionalAssessmentViewSet
from assessment.studentassessment import (
    AssessmentResponseViewSet,
    CareerDirectionViewSet,
    CareerValueViewSet,
    ConcernViewSet,
    NextQuestionViewSet,
    StudentAssessmentViewSet,
    UserGoalViewSet,
)

assessment_router = DefaultRouter()

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
assessment_router.register(
    "api/assessment-concern", ConcernViewSet, basename="assessment_concern"
)
assessment_router.register(
    "api/assessment-usergoal", UserGoalViewSet, basename="assessment_usergoal"
)
assessment_router.register(
    "api/assessment-careervalue", CareerValueViewSet, basename="assessment_careervalue"
)
assessment_router.register(
    "api/assessment-careerdirection",
    CareerDirectionViewSet,
    basename="assessment_careerdirection",
)
assessment_router.register(
    "api/parent/assessments",
    ParentAssessmentViewSet,
    basename="parent_assessment",
)
assessment_router.register(
    "api/professional/assessments",
    ProfessionalAssessmentViewSet,
    basename="professional_assessment",
)
