from django.db import transaction
from django.db.models import Q
from django.db.models.aggregates import Count
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.master_view import BaseModelViewSet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity_log.services import log_event
from assessment_career.models import CareerSuggestion
from common.master_view import BaseModelViewSet
from user.permissions import IsAdminOrProvider, is_admin_user

from .models import Job, JobApplication
from .serializers import JobApplicationSerializer, JobSerializer
from .service import match_jobs


class JobViewSet(BaseModelViewSet):
    def get_queryset(self):
        queryset = Job.objects.select_related(
            "city", "country", "state", "created_by", "job_provider"
        ).prefetch_related("education_tags")
        user = self.request.user
        if user.is_superuser:
            base = queryset
        elif user.user_type in [
            "corporate",
        ]:
            base = queryset.filter(job_provider=user)
        else:
            base = queryset.filter(status="active")
        if self.action not in [
            "restore",
            "archive_list",
            "archive",
            "bulk_archive",
            "bulk_restore",
            "destroy",
        ]:
            base = base.filter(deleted=False)

        from subscription.services.usage import apply_portal_limit

        return apply_portal_limit(user, base, "job")

    serializer_class = JobSerializer

    filter_backends = BaseModelViewSet.filter_backends + [DjangoFilterBackend]
    filterset_fields = {
        "status": ["exact"],
        "state": ["exact"],
        "city": ["exact"],
        "country": ["exact"],
        "experience_level": ["exact"],
        "job_type": ["exact"],
        "mode": ["exact"],
    }

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "job_provider__corporate_profile__company_name",
        "description",
        "job_overview",
        "education_tags__display_name",
        "experience_level",
        "job_type",
        "mode",
        "city__name",
        "state__name",
        "country__name",
        "job_provider__full_name",
        "why_this_match",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
        "description",
        "education_tags",
        "experience_level",
        "job_type",
        "mode",
        "city",
        "salary_min",
        "salary_max",
        "job_provider",
        "why_this_match",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            save_kwargs = {
                'created_by': request.user,
                'created_at': timezone.now(),
            }
            if request.user.user_type in ['corporate'] and 'job_provider' not in serializer.validated_data:
                save_kwargs['job_provider'] = request.user
            serializer.save(**save_kwargs)
            log_event(
                event="job.created",
                description=f"Created job {serializer.data.get('name')}",
                user=request.user,
                entity_type="job",
                entity_id=serializer.instance.id if serializer.instance else None,
                metadata={"job_name": serializer.data.get("name")},
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "data": serializer.data,
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

    @action(
        detail=False,
        methods=["patch"],
        url_path="update-status",
        permission_classes=[IsAuthenticated, IsAdminOrProvider],
    )
    @transaction.atomic
    def bulk_update_status(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])
        new_status = request.data.get("status")

        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in ["draft", "active", "closed"]:
            return Response(
                {
                    "success": False,
                    "message": "Status must be draft, active, or closed.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_admin = is_admin_user(request.user)

        jobs = Job.objects.filter(id__in=ids, deleted=False)
        if not is_admin:
            jobs = jobs.filter(job_provider=request.user)

        found_ids = set(jobs.values_list("id", flat=True))
        not_found_ids = list(set(ids) - found_ids)
        skipped_ids = list(jobs.filter(status=new_status).values_list("id", flat=True))
        updated_ids = list(jobs.exclude(status=new_status).values_list("id", flat=True))

        if updated_ids:
            Job.objects.filter(id__in=updated_ids).update(
                status=new_status,
                updated_at=timezone.now(),
                updated_by=request.user,
            )
            log_event(
                event="job.bulk_status_changed",
                description=(
                    f"Changed {len(updated_ids)} job(s) "
                    f"to {new_status}"
                ),
                user=request.user,
                entity_type="job",
                entity_id=None,
                metadata={
                    "job_ids": updated_ids,
                    "status": new_status,
                    "count": len(updated_ids),
                },
                request=request,
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_ids)} job(s) updated successfully.",
                "data": {
                    "updated_job_ids": updated_ids,
                    "skipped_job_ids": skipped_ids,
                    "not_found_job_ids": not_found_ids,
                },
            },
            status=status.HTTP_200_OK,
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
        log_event(
            event="job.restored",
            description=f"Restored job {instance.name}",
            user=request.user,
            entity_type="job",
            entity_id=instance.id,
            metadata={"job_name": instance.name},
            request=request,
        )
        return Response(
            {"success": True, "message": "Job restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="bulk-archive")
    @transaction.atomic
    def bulk_archive(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        records = Job.objects.filter(id__in=ids)
        if not request.user.is_superuser:
            if request.user.user_type in ["corporate"]:
                records = records.filter(job_provider=request.user)
            else:
                records = Job.objects.none()

        if not records.exists():
            return Response(
                {"success": False, "message": "Jobs not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=True).exists():
            return Response(
                {"success": False, "message": "Some jobs are already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        records.update(
            deleted=True,
            deleted_at=now,
            deleted_by=request.user,
        )

        log_event(
            event="job.bulk_archive",
            description=f"Bulk archived {records.count()} job(s)",
            user=request.user,
            entity_type="job",
            entity_id=None,
            metadata={"job_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Jobs archived successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], url_path="bulk-restore")
    @transaction.atomic
    def bulk_restore(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])

        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        records = Job.objects.filter(id__in=ids)
        if not request.user.is_superuser:
            if request.user.user_type in ["corporate"]:
                records = records.filter(job_provider=request.user)
            else:
                records = Job.objects.none()

        if not records.exists():
            return Response(
                {"success": False, "message": "Jobs not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=False).exists():
            return Response(
                {"success": False, "message": "Some jobs are already active"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        records.update(
            deleted=False,
            deleted_at=None,
            deleted_by=None,
            updated_at=now,
            updated_by=request.user,
        )

        log_event(
            event="job.bulk_restore",
            description=f"Bulk restored {records.count()} job(s)",
            user=request.user,
            entity_type="job",
            entity_id=None,
            metadata={"job_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Jobs restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archive-list")
    def archive_list(self, request):
        queryset = (
            Job.objects.select_related(
                "city", "country", "state", "created_by", "job_provider"
            )
            .prefetch_related("education_tags")
            .filter(deleted=True)
            .order_by("-deleted_at")
        )

        user = request.user
        if not user.is_superuser:
            if user.user_type in ["corporate"]:
                queryset = queryset.filter(job_provider=user)
            else:
                queryset = queryset.none()

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="job-recommended")
    def job_recommended(self, request):

        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        search = request.query_params.get("search")

        # Public listing: only active jobs, exclude drafts
        jobs_qs = self.get_queryset().filter(status="active", deleted=False)

        if mode:
            jobs_qs = jobs_qs.filter(mode=mode)

        if city_id:
            jobs_qs = jobs_qs.filter(city_id=city_id)

        if search:
            jobs_qs = jobs_qs.filter(name__icontains=search)

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
        jobs = match_jobs(
            ai_skills=career.required_skills or [],
            ai_education=career.required_education or {},
            user=request.user,
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
                "success": True,
                "count": len(data),
                "message": "Recommended Jobs",
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

    def get_queryset(self):
        user = self.request.user
        base = JobApplication.objects.select_related("applicant", "job")
        if user.is_superuser:
            return base
        if user.user_type in ["corporate"]:
            return base.filter(job__job_provider=user)
        return base.filter(applicant=user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        summary = queryset.aggregate(
            total_leads=Count("id"),
            applied_leads=Count("id", filter=Q(status="applied")),
            under_review_leads=Count("id", filter=Q(status="under_review")),
            selected_leads=Count("id", filter=Q(status="selected")),
            rejected_leads=Count("id", filter=Q(status="rejected")),
        )

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "success": True,
                    "summary": summary,
                    "count": queryset.count(),
                    "data": serializer.data,
                }
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {
                    "success": True,
                    "summary": summary,
                    "data": serializer.data,
                }
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "summary": summary,
                "count": queryset.count(),
                "data": serializer.data,
            }
        )

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
                {"success": False, "message": "You have already applied for this job"},
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
        data.pop("job", None)
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

    @action(detail=False, methods=["get"], url_path="received-inquiries")
    def receive_inquiries(self, request):
        inquiries = JobApplication.objects.filter(
            job__job_provider=request.user,
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
                "count": inquiries.count(),
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
    
    @action(detail=False, methods=["get"], url_path="my-applications")
    def my_applications(self, request):
        applications = JobApplication.objects.filter(
            applicant=request.user
        ).select_related("job")

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(applications, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(applications)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(applications, many=True)
        return Response(
            {
                "success": True,
                "count": applications.count(),
                "data": serializer.data,
            }
        )

    @action(detail=True, methods=["patch"], url_path="update-status")
    def update_status(self, request, pk=None):
        application = self.get_object()

        job = application.job
        if job.job_provider != request.user:
            return Response(
                {
                    "success": False,
                    "message": "You are not allowed to update this job application status",
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
        valid_statuses = {
            choice[0] for choice in JobApplication.APPLICATION_STATUS_CHOICE
        }
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
        log_event(
            event="job_application.status_changed",
            description=f"Changed application #{application.id} status to {application_status}",
            user=request.user,
            entity_type="job_application",
            entity_id=application.id,
            metadata={"job_id": application.job_id, "status": application_status},
            request=request,
        )
        return Response(
            {
                "success": True,
                "message": "Application status updated successfully",
                "data": self.get_serializer(application).data,
            },
            status=status.HTTP_200_OK,
        )
