from .views import (
    CareerSuggestionDetailViewSet,
    CareerSuggestionViewSet,
    ParentCareerSuggestionDetailViewSet,
    ParentCareerSuggestionViewSet,
)
from rest_framework.routers import DefaultRouter

assessment_career_router = DefaultRouter()
assessment_career_router.register(
    "api/career-suggestions", CareerSuggestionViewSet, basename="career_suggestions"
)
assessment_career_router.register(
    "api/career-suggestions-detail", CareerSuggestionDetailViewSet, basename="career_suggestion_detail"
)
assessment_career_router.register(
    "api/parent/career-suggestions", ParentCareerSuggestionViewSet, basename="parent_career_suggestions"
)
assessment_career_router.register(
    "api/parent/career-suggestions-detail", ParentCareerSuggestionDetailViewSet, basename="parent_career_suggestion_detail"
)