from datetime import date
from rest_framework.viewsets import ModelViewSet
from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.utils import timezone
from utils.generate_ip_address import get_client_ip
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from django.db import transaction


# Create your models here.
class FinancialYearModel(models.Model):
    fid = models.AutoField(primary_key=True)
    financial_year = models.CharField(max_length=15, default="")
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)
    approved_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"({self.fid} )"

    class Meta:
        db_table = "financial_year"


class BaseModule(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        user = kwargs.pop("user", None)
        if is_new:

            self.updated_at = None
            self.updated_by = None
            if user and not self.created_by:
                self.created_by = user
        else:
            old_deleted = getattr(self.__class__.objects.get(pk=self.pk), 'deleted', False) if self.pk else False
            current_deleted = getattr(self, 'deleted', False)
            
            if old_deleted == current_deleted and not current_deleted:
                self.updated_at = timezone.now()
            
            if user:
                self.updated_by = user

        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        """
        Soft delete the record by setting deleted=True, deleted_at, and deleted_by.
        This ensures audit trail is maintained.
        """
        self.deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        models.Model.save(self, update_fields=[
                          "deleted", "deleted_at", "deleted_by"])

        return (1, {self.__class__.__name__: [self.pk]})

class ArchiveMixin(ModelViewSet):
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
        except Exception as e:
            print("Logging Error:", str(e))

    @action(methods=["get"], detail=False, url_path="archive-list")
    def archive_list(self,request):
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
            return Response({"message":"Already archived"},status=400)
        instance.deleted=True
        instance.deleted_at = timezone.now()
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        instance.save()
        self.log_archive_action(request, instance=instance,action="ARCHIVE")
        return Response({"success":True, "message":"Archived Successfully"},status=status.HTTP_200_OK)
    
    @action(methods=["post"],detail=True)
    def restore(self, request, pk=None):
        instance = self.get_object()
        if not instance.deleted:
            return Response({"message":"Alredy Restored"}, status=status.HTTP_200_OK)
        instance.deleted = False
        instance.deleted_at = None
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = None
        instance.save()

        self.log_archive_action(request, instance=instance, action="RESTORE")
        return Response({"success":True, "message":"Restored Successfully"}, status=status.HTTP_200_OK)
    
    @action(methods=["post"],detail=False, url_path="bulk-archive")
    def bulk_archive(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response({"message":"Ids are Required"}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(id__in=ids, deleted=False)
        
        with transaction.atomic():
            queryset.update(deleted=True, deleted_at=timezone.now())
            for instance in queryset:
                if hasattr(instance, "deleted_by"):
                    instance.deleted_by = request.user
                    instance.save(update_fields=["deleted_by"])
        self.log_archive_action(request,queryset=queryset, action="ARCHIVE")
        return Response({"success":True, "message":"Bulk Archived Successfully"}, status=status.HTTP_200_OK)
    
    @action(methods=["post"], detail=False,url_path="bulk-restore")
    def bulk_restore(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"message":"IDs are Requires"},status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset().filter(id__in=ids, deleted=True)
        with transaction.atomic():
            queryset.update(deleted=False, deleted_at=None)
            # Clear deleted_by field for restored records
            for instance in queryset:
                if hasattr(instance, "deleted_by"):
                    instance.deleted_by = None
                    instance.save()
            self.log_archive_action(request,queryset=queryset, action="RESTORE")
            return Response({"success":True, "message":"Bulk Restore Successfully"},status=status.HTTP_200_OK)
