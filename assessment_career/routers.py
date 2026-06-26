from rest_framework.routers import DefaultRouter

from .views import (
    ParentCareerSuggestionDetailViewSet,
    ParentCareerSuggestionViewSet,
    StudentCareerSuggestionDetailViewSet,
    StudentCareerSuggestionViewSet,
)

assessment_career_router = DefaultRouter()

assessment_career_router.register(
    "api/career-suggestions",
    StudentCareerSuggestionViewSet,
    basename="career_suggestions",
)
assessment_career_router.register(
    "api/career-suggestions-detail",
    StudentCareerSuggestionDetailViewSet,
    basename="career_suggestion_detail",
)
assessment_career_router.register(
    "api/parent/career-suggestions",
    ParentCareerSuggestionViewSet,
    basename="parent_career_suggestions",
)
assessment_career_router.register(
    "api/parent/career-suggestions-detail",
    ParentCareerSuggestionDetailViewSet,
    basename="parent_career_suggestion_detail",
)
