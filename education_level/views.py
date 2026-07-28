from uuid import UUID

from django.core.cache import cache
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.mixins.view_mixins import SuccessEnvelopeMixin
from education_level.models import EducationLevel
from education_level.permissions import EducationLevelMasterPermission
from education_level.serializers import (
    EducationLevelBulkIdsSerializer,
    EducationLevelBulkImportSerializer,
    EducationLevelChangeStatusSerializer,
    EducationLevelDropdownSerializer,
    EducationLevelImportBatchSerializer,
    EducationLevelImportErrorSerializer,
    EducationLevelReorderSerializer,
    EducationLevelSerializer,
)
from education_level.services import education_level_service
from utils.cache_keys import dropdown_key
from utils.custom_filters import CustomSearchFilter
from utils.pagination import Pagination


class EducationLevelViewSet(SuccessEnvelopeMixin, ModelViewSet):
    serializer_class = EducationLevelSerializer
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = ["level_code", "display_name"]
    ordering_fields = [
        "level_code",
        "display_name",
        "sequence_order",
        "min_age",
        "max_age",
        "created_at",
        "updated_at",
    ]
    permission_classes = [EducationLevelMasterPermission]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        qs = education_level_service.education_level_base_queryset()
        act = getattr(self, "action", None)
        if act == "archived":
            return qs.filter(deleted=True).order_by("-updated_at", "-created_at")
        return qs.filter(deleted=False).order_by("sequence_order", "display_name")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        req = self.request.query_params
        if "is_active" in req:
            v = str(req.get("is_active")).lower()
            if v in ("true", "1", "yes"):
                queryset = queryset.filter(is_active=True)
            elif v in ("false", "0", "no"):
                queryset = queryset.filter(is_active=False)
        min_age = req.get("min_age")
        max_age = req.get("max_age")
        if min_age not in (None, ""):
            queryset = queryset.filter(max_age__gte=min_age)
        if max_age not in (None, ""):
            queryset = queryset.filter(min_age__lte=max_age)
        return queryset

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            UUID(str(pk))
        except (ValueError, TypeError):
            raise NotFound()
        qs = education_level_service.education_level_base_queryset().filter(
            deleted=False
        )
        try:
            return qs.get(pk=pk)
        except EducationLevel.DoesNotExist:
            raise NotFound()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Education level created",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            education_level_service.archive_level(level=instance, user=request.user)
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"success": True, "message": "Archived Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="archived")
    def archived(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = EducationLevelSerializer(
                queryset, many=True, context={"request": request}
            )
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = EducationLevelSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = EducationLevelSerializer(
            queryset, many=True, context={"request": request}
        )
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        ser = EducationLevelChangeStatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        education_level_service.set_active_status(
            level=instance,
            user=request.user,
            is_active=ser.validated_data["is_active"],
        )
        instance.refresh_from_db()
        return Response(
            {
                "success": True,
                "data": EducationLevelSerializer(
                    instance, context={"request": request}
                ).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request, *args, **kwargs):
        key = dropdown_key("education_level")
        try:
            cached = cache.get(key)
        except Exception:
            cached = None
        if cached is not None:
            return Response({"success": True, "data": cached})

        qs = education_level_service.dropdown_levels()
        serializer = EducationLevelDropdownSerializer(qs, many=True)
        data = serializer.data
        try:
            cache.set(key, data, 60 * 60)
        except Exception:
            pass
        return Response({"success": True, "data": data})

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request, *args, **kwargs):
        ser = EducationLevelReorderSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        count = education_level_service.reorder_levels(
            orders=ser.validated_data["orders"],
            user=request.user,
        )
        return Response(
            {"success": True, "message": "Reordered successfully", "count": count}
        )

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        ser = EducationLevelBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            n = education_level_service.bulk_archive(
                ids=list(ser.validated_data["ids"]), user=request.user
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"success": True, "message": "Bulk archived successfully", "count": n}
        )

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        ser = EducationLevelBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        n = education_level_service.bulk_restore(
            ids=list(ser.validated_data["ids"]), user=request.user
        )
        return Response(
            {"success": True, "message": "Bulk restored successfully", "count": n}
        )

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request, *args, **kwargs):
        ser = EducationLevelBulkImportSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        batch = education_level_service.bulk_import_rows(
            user=request.user,
            rows=ser.validated_data["rows"],
            serializer_class=EducationLevelSerializer,
            context={"request": request},
        )
        return Response(
            {
                "success": True,
                "data": EducationLevelImportBatchSerializer(
                    batch, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        rows, parse_errors = education_level_service.parse_import_file(upload)
        if not rows:
            msg = parse_errors or ["No data rows in file."]
            return Response(
                {"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST
            )
        result = education_level_service.bulk_import_levels(
            user=request.user,
            rows=rows,
            serializer_class=EducationLevelSerializer,
            context={"request": request},
        )
        payload = {
            "success": True,
            "success_count": result["success_count"],
            "error_count": result["error_count"],
            "error_details": result["error_details"],
            "batch_id": result["batch_id"],
        }
        if parse_errors:
            payload["parse_warnings"] = parse_errors
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request, *args, **kwargs):
        qs = education_level_service.import_batches_queryset()
        page = self.paginate_queryset(qs)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = EducationLevelImportBatchSerializer(
                qs, many=True, context={"request": request}
            )
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = EducationLevelImportBatchSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = EducationLevelImportBatchSerializer(
            qs, many=True, context={"request": request}
        )
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="import-errors")
    def import_errors(self, request, *args, **kwargs):
        batch_id = request.query_params.get("batch_id")
        bid = None
        if batch_id:
            try:
                bid = UUID(str(batch_id))
            except (ValueError, TypeError):
                return Response(
                    {"success": False, "message": "Invalid batch_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        qs = education_level_service.import_errors_queryset(batch_id=bid)
        page = self.paginate_queryset(qs)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = EducationLevelImportErrorSerializer(qs, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = EducationLevelImportErrorSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = EducationLevelImportErrorSerializer(qs, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="error-report/download")
    def error_report_download(self, request, *args, **kwargs):
        batch_id = request.query_params.get("batch_id")
        bid = None
        if batch_id:
            try:
                bid = UUID(str(batch_id))
            except (ValueError, TypeError):
                return Response(
                    {"success": False, "message": "Invalid batch_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        filename, data = education_level_service.error_report_csv_bytes(batch_id=bid)
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
