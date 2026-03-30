from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from user_skill.models import UserSkill
from user_skill.serializers import UserSkillSerializer


class UserSkillViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserSkillSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        return UserSkill.objects.filter(user=self.request.user, deleted=False).order_by("-updated_at", "id")
