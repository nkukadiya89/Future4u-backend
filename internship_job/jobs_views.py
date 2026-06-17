from .models import Job, JobApplication
from .serializers import JobSerializer, JobApplicationSerializer
from rest_framework import status
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.response import Response
from common.master_view import BaseModelViewSet
from django.utils import timezone
from assessment_career.models import CareerRecommendationSuggestion
from .service import match_jobs


class JobViewSet(BaseModelViewSet):
    def get_queryset(self):
        queryset = Job.objects.select_related("city", "provider").prefetch_related("education_tags")
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
        
    serializer_class = JobSerializer

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "organization_name",
        "description",
        "skills",
        "responsibilities",
        "education_tags__name",
        "experience_level",
        "job_type",
        "mode",
        "city__name",
        "salary_min",
        "salary_max",
        "provider__full_name",
        "why_this_match",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields+[
        "name",
        "organization_name",
        "description",
        "education_tags",
        "experience_level",
        "job_type",
        "mode",
        "city",
        "salary_min",
        "salary_max",
        "provider",
        "why_this_match",
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
                {
                    "success":True,
                    "data":serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {
                "success": False,
                "message": serializer.errors,
            },
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
            {"success": True, "message": "Job restored successfully"},
            status=status.HTTP_200_OK,
        )
    

    @action(detail=False, methods=["get"], url_path="job-recommended")
    def job_recommended(self, request):
        
        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        search = request.query_params.get("search")

        jobs_qs = self.get_queryset().filter(status="active", deleted=False)

        if mode:
            jobs_qs = jobs_qs.filter(mode=mode)
            
        if city_id:
            jobs_qs = jobs_qs.filter(city_id=city_id)
        
        if search:
            jobs_qs = jobs_qs.filter(
                name__icontains=search
            )
        
        if request.user.user_type in [
            "student",
            "parent",
        ]:
            jobs_qs = jobs_qs.filter(
                experience_level__in=[
                    "fresher",
                    "0_1",
                ]
            )
        career_id = request.query_params.get("career_id")

        if not career_id:
            return Response(
                {
                    "success": False,
                    "message": "Career_id is Required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            career = (
                CareerRecommendationSuggestion.objects.get(
                    id=career_id,
                    recommendation__user = request.user,
                    deleted=False,
                    recommendation__deleted=False
                )
            )
        except CareerRecommendationSuggestion.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Career not found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        jobs = match_jobs(
            ai_skills=career.required_skills or [],
            ai_education=career.required_education or {},
            user = request.user,
            jobs_qs=jobs_qs,
        )

        data = []

        for item in jobs:
            serializer_data = self.get_serializer(item["job"]).data
            data.append(
                {
                    "score": item["score"],
                    "skill_matches": item["skill_matches"],
                    "job": serializer_data,
                }
            )
        return Response(
            {
                "success" : True,
                "count": len(data),
                "message":"Recommended Jobs",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )
        

class JobApplicationViewSet(BaseModelViewSet):

    queryset = JobApplication.objects.select_related("applicant", "job")
    serializer_class = JobApplicationSerializer

    search_fields = BaseModelViewSet.searching_fields + [
        "applicant__full_name",
        "job__name",
        "status",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "applicant",
        "job",
        "status",
        "applied_at",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        job_id = request.data.get("job")
        resume_file = request.FILES.get("resume")

        if not job_id:
            return Response(
                {
                    "success": False,
                    "message": "job id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            job = Job.objects.get(
                id=job_id,
                deleted=False,
                status="active",
            )
        except Job.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Job Not Found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if JobApplication.objects.filter(
            applicant=request.user,
            job=job,
            deleted=False,
        ).exists():
            return Response(
                {
                    "success": False,
                    "message": "You have already applied for this job"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        application = JobApplication.objects.create(
            applicant=request.user,
            job=job,
            created_by=request.user,
            created_at=timezone.now(),
            status="applied",
        )

        if resume_file:
            application.upload_resume(resume_file)
        serializer = self.get_serializer(application)

        return Response(
            {
                "success": True,
                "message": "Job Applied successfully",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    
    
    @transaction.atomic()
    def update(self, request, *args, **kwargs):
        application = self.get_object()

        if application.applicant != request.user:
            return Response(
                {
                    "success":False,
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
        data.pop("job", None)
        data.pop("status", None)

        serializer = self.get_serializer(
            application, data=data,
            partial=True
        )

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
    def my_inquiries(self, request):
        inquiries = JobApplication.objects.filter(
            applicant=request.user,
            deleted=False,
        ).select_related("applicant", "job")

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
        inquiries = JobApplication.objects.filter(
            job__provider=request.user,
            deleted=False,
        ).select_related("job", "applicant")
        
        job_id = request.query_params.get("job_id")

        if not job_id:
            return Response(
                {
                    "success": False,
                    "message": "Job id is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        inquiries = inquiries.filter(job_id=job_id)
        serializer = self.get_serializer(inquiries, many=True)
        return Response(
            {
                "success": True,
                "count" : inquiries.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=True, methods=["patch"], url_path="update-status")
    def update_status(self, request, pk=None):
        application = self.get_object()

        if application.job.provider != request.user:
            return Response(
                {
                    "success":False,
                    "message":"You are not allowed to update this job application status",
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
        valid_statuses = {choice[0] for choice in JobApplication.APPLICATION_STATUS_CHOICE}
        if application_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "message": f"Invalid status. Allowed: {', '.join(sorted(valid_statuses))}",
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
    
    