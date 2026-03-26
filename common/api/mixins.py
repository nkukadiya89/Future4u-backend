import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from utils.generate_ip_address import get_client_ip

logger = logging.getLogger(__name__)


class ArchiveMixin(ModelViewSet):
    """
    ViewSet mixin for archive/restore based on BaseModule soft-delete fields:
    - archived == deleted=True
    """

    def log_archive_action(self, request, instance=None, action=None, queryset=None):
        from activity_log.models import ActivityLog

        ip_address = get_client_ip(request)
        queryset = self.get_queryset()
        model_name = queryset.model.__name__.lower()
        try:
            if action == "ARCHIVE":
                method_name = f"{model_name}_archive"
            elif action == "RESTORE":
                method_name = f"{model_name}_restore"
            else:
                return
            if hasattr(ActivityLog.log, method_name):
                log_method = getattr(ActivityLog.log, method_name)

                if instance:
                    log_method(instance, ip_address=ip_address, user=request.user)
                elif queryset:
                    for obj in queryset:
                        log_method(obj, ip_address=ip_address, user=request.user)
        except Exception:
            logger.exception("ActivityLog archive logging failed")

    @action(methods=["get"], detail=False, url_path="archive-list")
    def archive_list(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(deleted=True).order_by("-deleted_at"))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=["post"], detail=True)
    def archive(self, request, pk=None):
        instance = self.get_object()
        if instance.deleted:
            return Response({"message": "Already archived"}, status=400)
        instance.deleted = True
        instance.deleted_at = timezone.now()
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        instance.save()
        self.log_archive_action(request, instance=instance, action="ARCHIVE")
        return Response(
            {"success": True, "message": "Archived Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=True)
    def restore(self, request, pk=None):
        instance = self.get_object()
        if not instance.deleted:
            return Response({"message": "Alredy Restored"}, status=status.HTTP_200_OK)
        instance.deleted = False
        instance.deleted_at = None
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = None
        instance.save()

        self.log_archive_action(request, instance=instance, action="RESTORE")
        return Response(
            {"success": True, "message": "Restored Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=False, url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response({"message": "Ids are Required"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(id__in=ids, deleted=False)

        with transaction.atomic():
            queryset.update(deleted=True, deleted_at=timezone.now())
            for instance in queryset:
                if hasattr(instance, "deleted_by"):
                    instance.deleted_by = request.user
                    instance.save(update_fields=["deleted_by"])
        self.log_archive_action(request, queryset=queryset, action="ARCHIVE")
        return Response(
            {"success": True, "message": "Bulk Archived Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=False, url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"message": "IDs are Requires"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(id__in=ids, deleted=True)
        with transaction.atomic():
            queryset.update(deleted=False, deleted_at=None)
            for instance in queryset:
                if hasattr(instance, "deleted_by"):
                    instance.deleted_by = None
                    instance.save()
            self.log_archive_action(request, queryset=queryset, action="RESTORE")
            return Response(
                {"success": True, "message": "Bulk Restore Successfully"},
                status=status.HTTP_200_OK,
            )

