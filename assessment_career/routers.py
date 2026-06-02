from .views import CareerSuggestionViewSet,CareerSuggestionDetailViewSet
from rest_framework.routers import DefaultRouter

assessment_career_router = DefaultRouter()
assessment_career_router.register(
    "api/career-suggestions", CareerSuggestionViewSet, basename="career_suggestions"
)
assessment_career_router.register("api/career-suggestions-detail",CareerSuggestionDetailViewSet,basename="career_suggestion_detail")