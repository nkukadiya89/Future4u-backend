from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import Question, UserResponse
from assessment.services.recommendation_engine_service import RecommendationEngineService
from assessment.serializers import QuestionSerializer, UserResponseSerializer


class QuestionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Question.objects.filter(is_active=True).order_by("id")
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


class UserResponseViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = UserResponse.objects.all().order_by("id")
    serializer_class = UserResponseSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=["get"], url_path="recommendation")
    def recommendation(self, request, *args, **kwargs):
        result = RecommendationEngineService().recommend(user_id=request.user.id)
        return Response({"success": True, "data": result}, status=status.HTTP_200_OK)
