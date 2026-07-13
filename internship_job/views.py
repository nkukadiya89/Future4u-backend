from django.shortcuts import render
from .models import Internship, InternshipApplication
from .serializers import InternshipSerializer, InternshipApplicationSerializer
from common.master_view import BaseModelViewSet
from rest_framework import status
from rest_framework.response import Response
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import action
from rest_framework import status
from assessment_career.models import CareerSuggestion
from .service import match_internships

# Create your views here.


class InternshipViewSet(BaseModelViewSet):
    def get_queryset(self):
        queryset = Internship.objects.select_related(
            "city", "provider"
        ).prefetch_related("education_tags")
        user = self.request.user
        if user.is_superuser:
            return queryset
        if user.user_type in [
            "institute",
            "school_college",
            "corporate",
        ]:
            return queryset.filter(
                provider=user,
            )
        return queryset

    serializer_class = InternshipSerializer

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "organization_name",
        "description",
        "responsibilities",
        "skills",
        "education_tags",
        "why_this_match",
        "mode",
        "duration",
        "city__name",
        "internship_type",
        "fees_amount",
        "stipend_amount",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
        "organization_name",
        "internship_type",
        "mode",
        "provider",
        "city",
        "duration",
        "fees_amount",
        "stipend_amount",
        "certificate_provided",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                provider=request.user,
                created_by=request.user,
                created_at=timezone.now(),
            )
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(methods=["patch"], detail=True, url_path="restore")
    def restore(self, request, pk=None):
        instance = self.get_object()
        if not instance.deleted:
            return Response(
                {"success": False, "message": "Record is not archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.deleted = False
        instance.deleted_at = None
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = None
        if hasattr(instance, "updated_by"):
            instance.updated_by = request.user
        if hasattr(instance, "updated_at"):
            instance.updated_at = timezone.now()
        instance.save()
        return Response(
            {"success": True, "message": "Internship restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="internship-recommended")
    def internship_recommended(self, request):
        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        search = request.query_params.get("search")

        internship_qs = self.get_queryset()

        if mode:
            internship_qs = internship_qs.filter(mode=mode)
        if city_id:
            internship_qs = internship_qs.filter(city__id=city_id)
        if search:
            internship_qs = internship_qs.filter(title__icontains=search)

        career_id = request.query_params.get("career_id")
        if not career_id:
            return Response(
                {
                    "success": False,
                    "message": "Carrer_id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            career = CareerSuggestion.objects.get(
                id=career_id,
                recommendation__user=request.user,
                deleted=False,
                recommendation__deleted=False,
            )
        except CareerSuggestion.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Career not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        internships = match_internships(
            ai_skills=career.required_skills or [],
            ai_education=career.required_education or {},
            user=request.user,
            internships_qs=internship_qs,
        )
        data = []

        for item in internships:
            serializer_data = self.get_serializer(item["internship"]).data

            data.append(
                {
                    "score": item["score"],
                    "skill_matches": item["skill_matches"],
                    "internship": serializer_data,
                }
            )
        return Response(
            {
                "success": True,
                "count": len(data),
                "message": "Recommended internships",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class InternshipApplicationViewSet(BaseModelViewSet):
    queryset = InternshipApplication.objects.select_related("internship", "applicant")
    serializer_class = InternshipApplicationSerializer

    searching_fields = BaseModelViewSet.searching_fields + [
        "internship__name",
        "applicant__full_name",
        "applicant__user_type",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "internship",
        "applicant",
        "status",
        "applied_at",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        internship_id = request.data.get("internship")
        resume_file = request.FILES.get("resume")

        if not internship_id:
            return Response(
                {"success": False, "message": "Internship id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            internship = Internship.objects.get(
                id=internship_id,
                deleted=False,
            )
        except Internship.DoesNotExist:
            return Response(
                {"success": False, "message": "Internship Not Found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if InternshipApplication.objects.filter(
            applicant=request.user,
            internship=internship,
            deleted=False,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": "You have an already applied for this internship",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        application = InternshipApplication.objects.create(
            applicant=request.user,
            internship=internship,
            created_by=request.user,
            created_at=timezone.now(),
            status="applied",
        )

        if resume_file:
            application.upload_resume(resume_file)

        serialzer = self.get_serializer(application)

        return (
            Response(
                {
                    "success": True,
                    "message": "Internship Applied successfully",
                    "data": serialzer.data,
                },
                status=status.HTTP_201_CREATED,
            ),
        )

    @transaction.atomic()
    def update(self, request, *args, **kwargs):
        application = self.get_object()

        if application.applicant != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to update this application",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if application.status != "applied":
            return Response(
                {
                    "success": False,
                    "message": "Application can update only when status is applied.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        resume_file = request.FILES.get("resume")
        if resume_file:
            application.upload_resume(resume_file)

        data = request.data.dict()
        data.pop("resume", None)
        data.pop("applicant", None)
        data.pop("internship", None)
        data.pop("status", None)

        serializer = self.get_serializer(application, data=data, partial=True)

        serializer.is_valid(raise_exception=True)
        serializer.save(
            updated_by=request.user,
            updated_at=timezone.now(),
        )
        return Response(
            {
                "success": True,
                "message": "Application updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="my-inquiries")
    def my_inquiry(self, request):
        inquiries = InternshipApplication.objects.filter(
            applicant=request.user,
            deleted=False,
        ).select_related("internship", "applicant")

        serializer = self.get_serializer(inquiries, many=True)
        return Response(
            {
                "success": True,
                "count": inquiries.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="received-inquiries")
    def receive_inquiries(self, request):
        inquiries = InternshipApplication.objects.filter(
            internship__provider=request.user,
            deleted=False,
        ).select_related("internship", "applicant")

        internship_id = request.query_params.get("internship_id")
        if not internship_id:
            return Response(
                {
                    "success": False,
                    "message": "Internship id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if internship_id:
            inquiries = inquiries.filter(internship_id=internship_id)
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
        application = self.get_object()

        if application.internship.provider != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to update this internship application status",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        application_status = request.data.get("status")
        if not application_status:
            return Response(
                {
                    "success": False,
                    "message": "status is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = application_status
        application.updated_by = request.user
        application.updated_at = timezone.now()
        application.save(update_fields=["status"])

        return Response(
            {
                "success": True,
                "message": "Application status updated successfully",
                "data": self.get_serializer(application).data,
            },
            status=status.HTTP_200_OK,
        )
