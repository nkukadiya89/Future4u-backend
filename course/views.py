from django.db import transaction
from django.db.models import Q
from django.db.models.aggregates import Count
from assessment_career.models import CareerSuggestion
from common.master_view import BaseModelViewSet
from course.services import match_courses
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity_log.services import log_event
from assessment_career.models import CareerSuggestion
from common.master_view import BaseModelViewSet
from course.services import match_courses
from user.permissions import IsAdminOrProvider, is_admin_user

from .models import CourseInquiry, Courses
from .serializers import CourseInquirySerializer, CoursesSerializer


class CoursesViewSet(BaseModelViewSet):
    def get_queryset(self):
        queryset = Courses.objects.select_related(
            "country", "state", "city", "provider"
        ).prefetch_related("education_tags")
        
        user = self.request.user
        if user.is_superuser:
            base = queryset
        elif user.user_type in [
            "institute",
            "school_college",
        ]:
            base = queryset.filter(provider=user)
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

        return apply_portal_limit(user, base, "course")

    serializer_class = CoursesSerializer

    filter_backends = BaseModelViewSet.filter_backends + [DjangoFilterBackend]
    filterset_fields = {
        "status": ["exact"],
        "state": ["exact"],
        "city": ["exact"],
        "country": ["exact"],
        "course_type": ["exact"],
        "mode": ["exact"],
    }

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "course_type",
        "mode",
        "duration",
        "city__name",
        "country__name",
        "state__name",
        "course_overview",
        "course_description",
        "why_this_course",
        "certification_info",
        "course_price",
        "provider__full_name",
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

        courses = Courses.objects.filter(id__in=ids, deleted=False)
        if not is_admin:
            courses = courses.filter(provider=request.user)

        found_ids = set(courses.values_list("id", flat=True))
        not_found_ids = list(set(ids) - found_ids)
        skipped_ids = list(
            courses.filter(status=new_status).values_list("id", flat=True)
        )
        updated_ids = list(
            courses.exclude(status=new_status).values_list("id", flat=True)
        )

        if updated_ids:
            Courses.objects.filter(id__in=updated_ids).update(
                status=new_status,
                updated_at=timezone.now(),
                updated_by=request.user,
            )
            log_event(
                event="course.bulk_status_changed",
                description=(
                    f"{request.user.email} changed {len(updated_ids)} course(s) "
                    f"to {new_status}"
                ),
                user=request.user,
                entity_type="course",
                entity_id=None,
                metadata={
                    "course_ids": updated_ids,
                    "status": new_status,
                    "count": len(updated_ids),
                },
                request=request,
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_ids)} course(s) updated successfully.",
                "data": {
                    "updated_course_ids": updated_ids,
                    "skipped_course_ids": skipped_ids,
                    "not_found_course_ids": not_found_ids,
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
            {"success": True, "message": "Course restored successfully"},
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

        records = Courses.objects.filter(id__in=ids)

        if not records.exists():
            return Response(
                {"success": False, "message": "Courses not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=True).exists():
            return Response(
                {"success": False, "message": "Some courses are already archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        records.update(
            deleted=True,
            deleted_at=now,
            deleted_by=request.user,
        )

        log_event(
            event="course.bulk_archive",
            description=f"Admin {request.user.email} bulk archived {records.count()} course(s)",
            user=request.user,
            entity_type="course",
            entity_id=None,
            metadata={"course_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Courses archived successfully"},
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

        records = Courses.objects.filter(id__in=ids)

        if not records.exists():
            return Response(
                {"success": False, "message": "Courses not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if records.filter(deleted=False).exists():
            return Response(
                {"success": False, "message": "Some courses are already active"},
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
            event="course.bulk_restore",
            description=f"Admin {request.user.email} bulk restored {records.count()} course(s)",
            user=request.user,
            entity_type="course",
            entity_id=None,
            metadata={"course_ids": ids, "count": records.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Courses restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archive-list")
    def archive_list(self, request):
        queryset = Courses.objects.select_related(
            "country", "state", "city", "provider"
        ).prefetch_related("education_tags").filter(deleted=True).order_by("-deleted_at")

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

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

    def get_queryset(self):
        user = self.request.user
        base = CourseInquiry.objects.select_related("course")
        if user.is_superuser:
            return base
        if user.user_type in ["school_college", "institute"]:
            return base.filter(course__provider=user)
        return base.filter(user=user).filter(user=user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        summary = queryset.aggregate(
            total_leads=Count("id"),
            pending_leads=Count("id", filter=Q(status="pending")),
            responded_leads=Count("id", filter=Q(status="responded")),
            closed_leads=Count("id", filter=Q(status="closed")),
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            course = serializer.validated_data.get("course")
            career_suggestion = serializer.validated_data["career_suggestion"]
            if course.deleted or course.status != "active":
                return Response(
                    {
                        "success": False,
                        "message": "Course is not available for inquiries.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            if career_suggestion.recommendation.user != request.user:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid Career suggestion.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if CourseInquiry.objects.filter(user=request.user, course=course, career_suggestion=career_suggestion).exists():
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

    @action(detail=False, methods=["get"], url_path="received-inquiries")
    def received_inquiries(self, request):
        inquiries = CourseInquiry.objects.filter(course__provider=request.user)

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

    @action(detail=False, methods=["get"], url_path="my-inquiries")
    def my_inquiries(self, request):
        inquiries = CourseInquiry.objects.filter(user=request.user).select_related(
            "course"
        )

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(inquiries, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(inquiries)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(inquiries, many=True)
        return Response(
            {
                "success": True,
                "count": inquiries.count(),
                "data": serializer.data,
            }
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
