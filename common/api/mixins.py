import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

logger = logging.getLogger(__name__)


class ArchiveMixin(ModelViewSet):
    """
    ViewSet mixin for archive/restore based on BaseModule soft-delete fields:
    - archived == deleted=True
    """

    def log_archive_action(self, request, instance=None, action=None, queryset=None):
        from activity_log.services import log_event

        event = "master.deleted" if action == "ARCHIVE" else "master.restored"
        try:
            if instance:
                log_event(
                    event=event,
                    description=f"{instance.__class__.__name__} {action.lower()}d by {request.user.email}",
                    user=request.user,
                    entity_type=instance.__class__.__name__.lower(),
                    entity_id=getattr(instance, "id", None),
                    request=request,
                )
            elif queryset:
                for obj in queryset:
                    log_event(
                        event=event,
                        description=f"{obj.__class__.__name__} {action.lower()}d by {request.user.email}",
                        user=request.user,
                        entity_type=obj.__class__.__name__.lower(),
                        entity_id=getattr(obj, "id", None),
                        request=request,
                    )
        except Exception:
            logger.exception("ActivityLog archive logging failed")

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

        self.log_archive_action(request, instance=instance, action="RESTORE")
        return Response(
            {"success": True, "message": "Restored Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["post"], detail=False, url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response(
                {"message": "Ids are Required"}, status=status.HTTP_400_BAD_REQUEST
            )
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
            return Response(
                {"message": "IDs are Requires"}, status=status.HTTP_400_BAD_REQUEST
            )
        queryset = self.get_queryset().filter(id__in=ids, deleted=True)
        with transaction.atomic():
            for instance in queryset:
                instance.deleted = False
                instance.deleted_at = None
                if hasattr(instance, "deleted_by"):
                    instance.deleted_by = None
                if hasattr(instance, "updated_by"):
                    instance.updated_by = request.user
                if hasattr(instance, "updated_at"):
                    instance.updated_at = timezone.now()
                instance.save()
        self.log_archive_action(request, queryset=queryset, action="RESTORE")
        return Response(
            {"success": True, "message": "Bulk Restore Successfully"},
            status=status.HTTP_200_OK,
        )
