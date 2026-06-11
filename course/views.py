from assessment_career.models import CareerRecommendationSuggestion
from common.master_view import BaseModelViewSet
from course.services import match_courses
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import CourseInquiry, Courses
from .serializers import CourseInquirySerializer, CoursesSerializer


class CoursesViewSet(BaseModelViewSet):
    queryset = Courses.objects.all()
    serializer_class = CoursesSerializer

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "course_type",
        "skills",
        "education_tags",
        "mode",
        "duration",
        "city__name",
        "course_content",
        "course_overview",
        "certification_info",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
        "course_type",
        "mode",
        "provider",
        "city",
        "duration",
    ]
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                created_by=request.user,
                provider=request.user,
                created_at=timezone.now(),
            )
            return Response(
                {
                    "success": True,
                    "message": "Course Created Successfully",
                    "data": serializer.data,
                },
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
        courses_qs = self.get_queryset()

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
            career = CareerRecommendationSuggestion.objects.get(
                id=career_id,
                recommendation__user=request.user,
                deleted=False,
                recommendation__deleted=False,
            )
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
        data = []

        for item in courses:
            serialized_course = self.get_serializer(item["course"]).data

            data.append(
                {
                    "score": item["score"],
                    "courses": serialized_course,
                }
            )
        return Response(
            {
                "success": True,
                "count": len(data),
                "message": "Recommended courses",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class CourseInquiryViewSet(BaseModelViewSet):
    queryset = CourseInquiry.objects.all()
    serializer_class = CourseInquirySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            course = serializer.validated_data.get("course")
            if CourseInquiry.objects.filter(
                user=request.user,
                course=course
            ).exists():
                return Response(
                    {
                        "success": False,
                        "message": "You have already submitted an inquiry for this course.",
                    }
                )
            serializer.save(
                created_by=request.user,
                user=request.user,
                created_at=timezone.now(),
            )
            return Response(
                {
                    "success": True,
                    "message": "Inquiry Created Successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"], url_path="my-inquiries")
    def my_inquiries(self, request):
        inquiries = CourseInquiry.objects.filter(
            user=request.user
        ).select_related("course")

        serializer = self.get_serializer(inquiries, many=True)
        return Response(
            {
                "success": True,
                "count": inquiries.count(),
                "data": serializer.data,
            }
        )

    @action(detail=False, methods=["get"], url_path="received-inquiries")
    def received_inquiries(self, request):
        inquiries = CourseInquiry.objects.filter(
            course__provider=request.user
        )

        course_id = request.query_params.get("course_id")
        if not course_id:
            return Response(
                {"success": False, "message": "course_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if course_id:
            inquiries = inquiries.filter(course_id=course_id)
        serializer = self.get_serializer(inquiries, many=True)
        return Response(
            {
                "success": True,
                "count": inquiries.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
     
    @action(detail=True, methods=["patch"], url_path="update-status")
    def update_status(self, request, pk=None):
        inquiries = self.get_object()

        if inquiries.course.provider != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to update this course inquirie status",
                },
                status=status.HTTP_403_FORBIDDEN,
            )    
        inquiries_status = request.data.get("status")
        if not inquiries_status:
            return Response(
                {
                    "success": False,
                    "message": "status is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        inquiries.status = inquiries_status
        inquiries.save(update_fields=["status"])
        return Response(
            {
                "success": True,
                "message": "Inquiry status updated successfully",
                "data": self.get_serializer(inquiries).data,
            },
            status=status.HTTP_200_OK,
        )

