from rest_framework.viewsets import ModelViewSet

from common.mixins.view_mixins import ListEnvelopeMixin
from rest_framework.filters import OrderingFilter
from utils.custom_filters import CustomSearchFilter
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import status
from django.db import transaction
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.decorators import action


class CustomModelPermissions(DjangoModelPermissions):
    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


class BaseModelViewSet(ListEnvelopeMixin, ModelViewSet):
    filter_backends = [CustomSearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [CustomModelPermissions]
    authentication_classes = [JWTAuthentication]

    list_serializer_class = None

    searching_fields = [
        "created_by__first_name",
        "created_by__last_name",
        "updated_by__first_name",
        "updated_by__last_name",
        "deleted_by__first_name",
        "deleted_by__last_name",
        "created_by__full_name",
        "updated_by__full_name",
        "deleted_by__full_name",
    ]

    ordering_fields = [
        "created_by",
        "updated_by",
        "deleted_by",
        "created_at",
        "updated_at",
        "deleted_at",
    ]

    def get_serializer_class(self):
        if self.action == "list" and self.list_serializer_class:
            return self.list_serializer_class
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action not in [
            "archive_list",
            "archive",
            "restore",
            "bulk_archive",
            "bulk_restore",
            "destroy",
        ]:
            queryset = queryset.filter(deleted=False).order_by("-id")
        return queryset

    def log_action(self, request, instance, action):
        from activity_log.services import log_event

        model_name = instance.__class__.__name__
        event_map = {
            "CREATE": "master.created",
            "UPDATE": "master.updated",
            "ARCHIVE": "master.deleted",
        }
        event = event_map.get(action.upper(), f"master.{action.lower()}")
        log_event(
            event=event,
            description=f"{model_name} {action.lower()}d by {request.user.email}",
            user=request.user,
            entity_type=model_name.lower(),
            entity_id=getattr(instance, "id", None),
            request=request,
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by=request.user,
                created_at=timezone.now(),
            )
            self.log_action(request, instance, "CREATE")
            return Response(
                {
                    "success": True,
                    "message": "Record Created Successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save(
                updated_by=request.user,
                updated_at=timezone.now(),
            )
            self.log_action(request, instance, "UPDATE")
            return Response(
                {
                    "success": True,
                    "message": "Updated Successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if getattr(instance, "deleted", False):
            return Response(
                {"success": False, "message": "Already Archived"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.deleted = True
        instance.deleted_at = timezone.now()

        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        instance.save()

        if hasattr(self, "log_archive_action"):
            self.log_archive_action(request, instance=instance, action="ARCHIVE")
        return Response(
            {"success": True, "message": "Record Archived Successfully"},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if getattr(instance, "deleted", False):
            return Response(
                {"success": False, "message": "Record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(instance)

        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], detail=False, url_path="archive-list")
    def archive_list(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(deleted=True).order_by("-deleted_at")
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})
