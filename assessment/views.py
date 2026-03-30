from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import Question, UserResponse
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
