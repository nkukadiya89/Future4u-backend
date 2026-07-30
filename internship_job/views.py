from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from django.db.models.aggregates import Count
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from activity_log.services import log_event
from assessment_career.models import CareerSuggestion
from common.master_view import BaseModelViewSet
from user.permissions import IsAdminOrProvider, is_admin_user
from .models import Internship, InternshipApplication
from .serializers import InternshipApplicationSerializer, InternshipSerializer
from .service import match_internships

# Create your views here.


class InternshipViewSet(BaseModelViewSet):
    def get_queryset(self):
        queryset = Internship.objects.select_related(
            "country", "state", "city", "created_by", "internship_provider"
        ).prefetch_related("education_tags")
        user = self.request.user
        if user.is_superuser:
            base = queryset
        elif user.user_type in [
            "institute",
            "corporate",
        ]:
            base = queryset.filter(internship_provider=user)
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

        return apply_portal_limit(user, base, "internship")

    serializer_class = InternshipSerializer

    filter_backends = BaseModelViewSet.filter_backends + [DjangoFilterBackend]
    filterset_fields = {
        "status": ["exact"],
        "state": ["exact"],
        "city": ["exact"],
        "country": ["exact"],
        "internship_type": ["exact"],
        "mode": ["exact"],
        "certificate_provided": ["exact"],
    }

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "department",
        "description",
        "education_tags__display_name",
        "why_this_match",
        "mode",
        "duration",
        "country__name",
        "state__name",
        "city__name",
        "internship_type",
        "created_by__full_name",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
        "country",
        "state",
        "city",
        "internship_type",
        "mode",
        "created_by",
        "duration",
        "fees_amount",
        "stipend_amount",
        "certificate_provided",
    ]

    @transaction.atomic()
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            save_kwargs = {
                'created_by': request.user,
                'created_at': timezone.now(),
            }
            # Auto-set internship_provider when institute/corporate creates their own internship
            if request.user.user_type in ['institute', 'corporate'] and 'internship_provider' not in serializer.validated_data:
                save_kwargs['internship_provider'] = request.user
            serializer.save(**save_kwargs)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
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
                {
                    "success": False,
                    "message": "ids must be a non-empty list.",
                },
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

        internships = Internship.objects.filter(
            id__in=ids,
            deleted=False,
        )
        if not is_admin:
            internships = internships.filter(internship_provider=request.user)

        found_ids = set(internships.values_list("id", flat=True))
        not_found_ids = list(set(ids) - found_ids)
        skipped_ids = list(
            internships.filter(status=new_status).values_list("id", flat=True)
        )
        updated_ids = list(
            internships.exclude(status=new_status).values_list("id", flat=True)
        )

        if updated_ids:
            Internship.objects.filter(id__in=updated_ids).update(
                status=new_status,
                updated_at=timezone.now(),
                updated_by=request.user,
            )
            log_event(
                event="internship.bulk_status_changed",
                description=(
                    f"{request.user.email} changed {len(updated_ids)} "
                    f"internship(s) to {new_status}"
                ),
                user=request.user,
                entity_type="internship",
                entity_id=None,
                metadata={
                    "internship_ids": updated_ids,
                    "status": new_status,
                    "count": len(updated_ids),
                },
                request=request,
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_ids)} internship(s) updated successfully.",
                "data": {
                    "updated_internship_ids": updated_ids,
                    "skipped_internship_ids": skipped_ids,
                    "not_found_internship_ids": not_found_ids,
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
        return Response(
            {"success": True, "message": "Internship restored successfully"},
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

        records = Internship.objects.filter(id__in=ids)

        if not records.exists():
            return Response(
                {"success": False, "message": "Internships not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=True).exists():
            return Response(
                {"success": False, "message": "Some internships are already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        records.update(
            deleted=True,
            deleted_at=now,
            deleted_by=request.user,
        )

        log_event(
            event="internship.bulk_archive",
            description=f"Admin {request.user.email} bulk archived {records.count()} internship(s)",
            user=request.user,
            entity_type="internship",
            entity_id=None,
            metadata={"internship_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Internships archived successfully"},
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

        records = Internship.objects.filter(id__in=ids)

        if not records.exists():
            return Response(
                {"success": False, "message": "Internships not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=False).exists():
            return Response(
                {"success": False, "message": "Some internships are already active"},
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
            event="internship.bulk_restore",
            description=f"Admin {request.user.email} bulk restored {records.count()} internship(s)",
            user=request.user,
            entity_type="internship",
            entity_id=None,
            metadata={"internship_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Internships restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archive-list")
    def archive_list(self, request):
        queryset = (
            Internship.objects.select_related(
                "country", "state", "city", "created_by", "internship_provider"
            )
            .prefetch_related("education_tags")
            .filter(deleted=True)
            .order_by("-deleted_at")
        )

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="internship-recommended")
    def internship_recommended(self, request):
        mode = request.query_params.get("mode")
        city_id = request.query_params.get("city_id")
        search = request.query_params.get("search")

        # Public listing: only active internships, exclude drafts
        internship_qs = self.get_queryset().filter(status="active", deleted=False)

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

    def get_queryset(self):
        user = self.request.user
        base = InternshipApplication.objects.select_related("internship", "applicant")
        if user.is_superuser:
            return base
        if user.user_type in ["institute", "corporate"]:
            return base.filter(internship__internship_provider=user)
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
                status="active",
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

        serializer = self.get_serializer(application)

        return Response(
            {
                "success": True,
                "message": "Internship Applied successfully",
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

    @action(detail=False, methods=["get"], url_path="received-inquiries")
    def receive_inquiries(self, request):
        inquiries = InternshipApplication.objects.filter(
            internship__internship_provider=request.user,
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

    @action(detail=False, methods=["get"], url_path="my-applications")
    def my_applications(self, request):
        applications = InternshipApplication.objects.filter(
            applicant=request.user
        ).select_related("internship")

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

        if application.internship.internship_provider != request.user:
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
