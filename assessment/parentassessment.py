from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import ParentAssessment


class ParentAssessmentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        return ParentAssessment.objects.filter(
            user=self.request.user, deleted=False
        ).order_by("-created_at")

    def assessment_status(self, request):
        assessment = self.get_queryset().first()
        if not assessment:
            return Response(
                {
                    "success": True,
                    "has_assessment": False,
                    "assessment_id": None,
                    "is_completed": False,
                    "current_screen": ParentAssessment.Screen.PENDING,
                }
            )

        return Response(
            {
                "success": True,
                "has_assessment": True,
                "assessment_id": assessment.id,
                "is_completed": assessment.is_completed,
                "current_screen": assessment.current_screen,
            }
        )
