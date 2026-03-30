from rest_framework.routers import DefaultRouter

from assessment.views import QuestionViewSet, UserResponseViewSet

assessment_router = DefaultRouter()
assessment_router.register("assessment/questions", QuestionViewSet, basename="assessment_questions")
assessment_router.register("assessment/responses", UserResponseViewSet, basename="assessment_responses")
