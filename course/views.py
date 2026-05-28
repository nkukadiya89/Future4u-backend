from django.shortcuts import render
from common.master_view import BaseModelViewSet
from course.services import match_courses
from .models import Courses
from .serializers import CoursesSerializer
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework import status
from assessment_career.models import CareerRecommendationSuggestion
from django.utils import timezone
# Create your views here.

class CoursesViewSet(BaseModelViewSet):
    queryset = Courses.objects.all()
    serializer_class = CoursesSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by=request.user,
                provider = request.user,
                created_at=timezone.now(),
            )
            return Response(
                {"success": True, "mesage":"Course Created Successfully","data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


    @action(detail=False, methods=["get"], url_path="recommended")
    def recommended_courses(self, request): 

        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        course_type = request.query_params.get("course_type")
        search = request.query_params.get("search")
        courses_qs = Courses.objects.all()

        if mode:
            courses_qs = courses_qs.filter(mode=mode)
        if city_id:
            courses_qs = courses_qs.filter(city__id=city_id)
        if course_type:
            courses_qs = courses_qs.filter(course_type=course_type)
        if search:
            courses_qs = courses_qs.filter(name__icontains=search)

        career_id = request.query_params.get("career_id")
        if not career_id:
            return Response(
                {
                    "success": False,
                    "message": "career_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
    
        try:
            career = CareerRecommendationSuggestion.objects.get(id=career_id)
        except CareerRecommendationSuggestion.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Career Not Found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
        ai_skills = career.required_skills or []
        ai_education = career.required_education or {}
        
        courses = match_courses(
            ai_skills=ai_skills,
            ai_education=ai_education,
            user=request.user,
            courses_qs=courses_qs,
            )
        serializer = self.get_serializer(courses, many=True)
        return Response(
            {
                "success": True,
                "count": len(serializer.data),
                "message": "Recommended courses",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
