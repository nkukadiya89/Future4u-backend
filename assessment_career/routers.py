from .views import CareerSuggestionViewSet
from rest_framework.routers import DefaultRouter

assessment_career_router = DefaultRouter()
assessment_career_router.register(
    "api/career-suggestions", CareerSuggestionViewSet, basename="career_suggestions"
)
