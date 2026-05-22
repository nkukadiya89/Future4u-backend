from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from assessment.services.course_career_service import courses_for_assessment
from courses.serializers import CourseSerializer


class AIRecommendationCoursesAPIView(APIView):
    """
    GET /api/ai-recommendations/{assessment_id}/courses/
    Courses linked (via CourseCareerMapping) to careers from stored LLM suggestions.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, assessment_id, *args, **kwargs):
        courses = courses_for_assessment(
            assessment_id=assessment_id,
            user_id=request.user.id,
        )
        serializer = CourseSerializer(courses, many=True)
        return Response(
            {
                "success": True,
                "message": (
                    "Recommendations fetched successfully"
                    if courses
                    else "No course mappings found for AI-suggested careers. "
                    "Run AI recommendations first and seed CourseCareerMapping."
                ),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
