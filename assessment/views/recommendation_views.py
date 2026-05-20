from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.models import (
    AssessmentCareerRecommendation,
    AssessmentDomainScore,
    AssessmentSkillScore,
    CourseCareerMapping,
    StudentAssessment,
)
from assessment.serializers import (
    AssessmentCareerRecommendationSerializer,
    AssessmentDomainScoreSerializer,
    AssessmentSkillScoreSerializer,
)
from courses.serializers import CourseSerializer


class AssessmentRecommendationViewSet(viewsets.ViewSet):
    """
    GET /api/recommendations/{id}/careers|skills|domains|courses/
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def _get_assessment(self, request, pk):
        return get_object_or_404(
            StudentAssessment.objects.filter(deleted=False),
            id=pk,
            user=request.user,
        )

    def _completed_or_error(self, assessment):
        if not assessment.is_completed:
            return Response(
                {
                    "success": False,
                    "message": "Assessment not completed yet",
                    "data": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=["get"], url_path="careers")
    def careers(self, request, pk=None):
        assessment = self._get_assessment(request, pk)
        err = self._completed_or_error(assessment)
        if err:
            return err
        qs = assessment.career_recommendations.select_related("career").order_by(
            "rank", "-score"
        )
        serializer = AssessmentCareerRecommendationSerializer(qs, many=True)
        return Response(
            {
                "success": True,
                "message": "Recommendations fetched successfully",
                "data": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="skills")
    def skills(self, request, pk=None):
        assessment = self._get_assessment(request, pk)
        err = self._completed_or_error(assessment)
        if err:
            return err
        qs = assessment.skill_scores.select_related("skill").order_by("-score", "id")
        serializer = AssessmentSkillScoreSerializer(qs, many=True)
        return Response(
            {
                "success": True,
                "message": "Recommendations fetched successfully",
                "data": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="domains")
    def domains(self, request, pk=None):
        assessment = self._get_assessment(request, pk)
        err = self._completed_or_error(assessment)
        if err:
            return err
        qs = assessment.domain_scores.select_related("domain").order_by("-score", "id")
        serializer = AssessmentDomainScoreSerializer(qs, many=True)
        return Response(
            {
                "success": True,
                "message": "Recommendations fetched successfully",
                "data": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="courses")
    def courses(self, request, pk=None):
        assessment = self._get_assessment(request, pk)
        err = self._completed_or_error(assessment)
        if err:
            return err
        recommended_career_ids = AssessmentCareerRecommendation.objects.filter(
            assessment=assessment,
            is_recommended=True,
        ).values_list("career_id", flat=True)
        mappings = (
            CourseCareerMapping.objects.filter(career_id__in=recommended_career_ids)
            .select_related("course")
            .order_by("-relevance_score", "course_id")
        )
        # Preserve global relevance ordering while returning each course once.
        ordered_courses = []
        seen_course_ids = set()
        for row in mappings:
            if row.course_id in seen_course_ids:
                continue
            seen_course_ids.add(row.course_id)
            ordered_courses.append(row.course)
        serializer = CourseSerializer(ordered_courses, many=True)
        return Response(
            {
                "success": True,
                "message": "Recommendations fetched successfully",
                "data": serializer.data,
            }
        )
