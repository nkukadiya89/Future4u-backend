from rest_framework.routers import DefaultRouter

from assessment.views import AssessmentInterestCategoryViewSet
from assessment.student.views import (
    StudentAssessmentQuestionsViewSet,
    StudentAssessmentStatusViewSet,
    StudentAssessmentSubmitViewSet,
    StudentAssessmentSummaryViewSet,
    StudentInterestCategoriesViewSet,
    StudentInterestViewSet,
)

assessment_router = DefaultRouter()
assessment_router.register(
    "assessment-interest-categories",
    AssessmentInterestCategoryViewSet,
    basename="assessment_interest_categories",
)
assessment_router.register(
    "api/assessment/student/interest-categories",
    StudentInterestCategoriesViewSet,
    basename="student_assessment_interest_categories",
)
assessment_router.register(
    "api/assessment/student/interests",
    StudentInterestViewSet,
    basename="student_assessment_interests",
)
assessment_router.register(
    "api/assessment/student/questions",
    StudentAssessmentQuestionsViewSet,
    basename="student_assessment_questions",
)
assessment_router.register(
    "api/assessment/student/submit",
    StudentAssessmentSubmitViewSet,
    basename="student_assessment_submit",
)
assessment_router.register(
    "api/assessment/student/status",
    StudentAssessmentStatusViewSet,
    basename="student_assessment_status",
)
assessment_router.register(
    "api/assessment/student/summary",
    StudentAssessmentSummaryViewSet,
    basename="student_assessment_summary",
)
assessment_router.register(
    "api/assessment/questions",
    StudentAssessmentQuestionsViewSet,
    basename="api_assessment_questions",
)
assessment_router.register(
    "api/assessment/submit",
    StudentAssessmentSubmitViewSet,
    basename="api_assessment_submit",
)
assessment_router.register(
    "api/assessment/status",
    StudentAssessmentStatusViewSet,
    basename="api_assessment_status",
)
assessment_router.register(
    "api/assessment/summary",
    StudentAssessmentSummaryViewSet,
    basename="api_assessment_summary",
)
