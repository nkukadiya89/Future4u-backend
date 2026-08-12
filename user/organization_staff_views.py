from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.services import log_event
from common.master_view import BaseModelViewSet
from email_utils.send_email import send_activation_password_setup_email
from user.models import CustomGroup, User
from utils.datetime_formatter import format_datetime
from utils.pagination import Pagination

from .organization_staff_serializers import (
    OrganizationStaffListSerializer,
    OrganizationStaffSerializer,
)
from .permissions import IsAdminOrProvider, is_admin_user


def _available_roles(user):
    qs = CustomGroup.objects.filter(deleted=False).order_by(
        "sequence", "group_name"
    )
    if not is_admin_user(user):
        qs = qs.filter(created_by=user)
    return [
        {"role_id": r["id"], "role_name": r["group_name"]}
        for r in qs.values("id", "group_name")
    ]


class OrganizationStaffViewSet(BaseModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    pagination_class = Pagination
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [SearchFilter, OrderingFilter]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    search_fields = BaseModelViewSet.searching_fields + [
        "first_name",
        "last_name",
        "user_type",
        "email",
        "email_verified",
        "must_change_password",
        "phone",
        "address",
        "country__name",
        "states__name",
        "city__name",
        "is_active",
        "status",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "id",
        "first_name",
        "last_name",
        "user_type",
        "email",
        "phone",
        "address",
        "is_active",
        "status",
    ]

    def get_queryset(self):
        user = self.request.user
        return (
            User.objects.filter(
                created_by=user,
                user_type=user.user_type,
                deleted=False,
            )
            .exclude(id=user.id)
            .select_related("country", "states", "city")
            .prefetch_related("groups")
            .order_by("-id")
        )

    def get_serializer_class(self):
        if self.action == "create" or self.action in (
            "update",
            "partial_update",
        ):
            return OrganizationStaffSerializer
        return OrganizationStaffListSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            staff = serializer.save()
            log_event(
                event="staff.created",
                description=f"Created staff {staff.email}",
                user=request.user,
                entity_type="user",
                entity_id=staff.id,
                metadata={"staff_name": f"{staff.first_name} {staff.last_name}"},
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": "Staff created successfully. A password setup link has been sent to their email.",
                    "user_id": staff.id,
                    "user_type": staff.user_type,
                    "is_org_staff": True,
                    "must_change_password": True,
                    "created_by": staff.created_by_id,
                    "created_at": format_datetime(staff.created_at),
                    "profile_image": staff.profile_image,
                    "roles": _available_roles(request.user),
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        staff = self.get_object()
        serializer = self.get_serializer(staff)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        staff = self.get_object()
        serializer = self.get_serializer(
            staff, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            staff = serializer.save()
            log_event(
                event="staff.updated",
                description=f"Updated staff {staff.email}",
                user=request.user,
                entity_type="user",
                entity_id=staff.id,
                request=request,
            )
            return Response(
                {
                    "success": True,
                    "message": "Staff updated successfully",
                    "user_id": staff.id,
                    "user_type": staff.user_type,
                    "profile_image": staff.profile_image,
                    "roles": _available_roles(request.user),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["patch"], url_path="update-status")
    @transaction.atomic
    def update_status(self, request, *args, **kwargs):
        ids = request.data.get("ids", [])
        new_status = request.data.get("status")

        if not isinstance(ids, list) or not ids:
            return Response(
                {"success": False, "message": "ids must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in ["active", "inactive"]:
            return Response(
                {"success": False, "message": "Status must be active or inactive"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = self.get_queryset().filter(id__in=ids)

        found_ids = set(users.values_list("id", flat=True))
        not_found_ids = list(set(ids) - found_ids)

        skipped_ids = []
        updated_ids = []
        activated_users = []

        for user in users:
            if user.status == new_status:
                skipped_ids.append(user.id)
                continue

            old_status = user.status

            user.status = new_status
            user.is_active = new_status == "active"
            user.updated_by = request.user
            user.updated_at = timezone.now()

            user.save(update_fields=["status", "is_active", "updated_at", "updated_by"])

            updated_ids.append(user.id)
            if old_status in ["pending", "inactive"] and new_status == "active":
                activated_users.append(user)

            log_event(
                event="staff.status_changed",
                description=f"Changed staff {user.email} status from {old_status} to {new_status}",
                user=request.user,
                entity_type="user",
                entity_id=user.id,
                request=request,
            )

        if activated_users:
            transaction.on_commit(
                lambda: [
                    send_activation_password_setup_email(user)
                    for user in activated_users
                ]
            )

        return Response(
            {
                "success": True,
                "message": f"{len(updated_ids)} user(s) updated successfully.",
                "data": {
                    "updated_ids": updated_ids,
                    "skipped_ids": skipped_ids,
                    "not_found_ids": not_found_ids,
                },
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        staff = (
            User.objects.filter(
                id=pk,
                created_by=request.user,
                user_type=request.user.user_type,
            )
            .exclude(id=request.user.id)
            .first()
        )

        if not staff:
            return Response(
                {"success": False, "message": "Staff not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if staff.deleted:
            return Response(
                {"success": False, "message": "Staff is already archived."},
                status=status.HTTP_200_OK,
            )

        if staff.status == "active":
            return Response(
                {
                    "success": False,
                    "message": "Active staff can not delete. Please inactive this staff first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        staff.deleted = True
        staff.deleted_at = timezone.now()
        staff.deleted_by = request.user
        staff.save(update_fields=["deleted", "deleted_at", "deleted_by"])

        log_event(
            event="staff.deleted",
            description=f"Deleted staff {staff.email}",
            user=request.user,
            entity_type="user",
            entity_id=staff.id,
            request=request,
        )

        return Response(
            {"success": True, "message": "Staff deleted successfully"},
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

        users = User.objects.filter(
            id__in=ids,
            created_by=request.user,
            user_type=request.user.user_type,
        ).exclude(id=request.user.id)

        if not users.exists():
            return Response(
                {"success": False, "message": "Staff not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if users.filter(deleted=True).exists():
            return Response(
                {
                    "success": False,
                    "message": "Some staff are already archived.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if users.filter(status="active").exists():
            return Response(
                {
                    "success": False,
                    "message": "Active staff can not delete. Please inactive first.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        users.update(
            deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )

        log_event(
            event="staff.bulk_archive",
            description=f"Bulk archived {users.count()} staff",
            user=request.user,
            entity_type="user",
            entity_id=None,
            metadata={"user_ids": ids, "count": users.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Staff deleted successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archive-list")
    def archive_list(self, request, *args, **kwargs):
        user = request.user
        queryset = (
            User.objects.filter(
                created_by=user,
                user_type=user.user_type,
                deleted=True,
            )
            .exclude(id=user.id)
            .select_related("country", "states", "city")
            .prefetch_related("groups")
            .order_by("-deleted_at")
        )

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
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

        users = User.objects.filter(
            id__in=ids,
            created_by=request.user,
            user_type=request.user.user_type,
        ).exclude(id=request.user.id)

        if not users.exists():
            return Response(
                {"success": False, "message": "Staff not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if users.filter(deleted=False).exists():
            return Response(
                {"success": False, "message": "Some staff are already active"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users.update(
            deleted=False,
            deleted_at=None,
            deleted_by=None,
            updated_at=timezone.now(),
            updated_by=request.user,
        )

        log_event(
            event="staff.bulk_restore",
            description=f"Bulk restored {users.count()} staff",
            user=request.user,
            entity_type="user",
            entity_id=None,
            metadata={"user_ids": ids, "count": users.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Staff restored successfully"},
            status=status.HTTP_200_OK,
        )
