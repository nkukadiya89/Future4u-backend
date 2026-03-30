from uuid import UUID

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache

from skill.models import Skill
from skill.permissions import SkillMasterPermission
from skill.serializers import (
    SkillBulkIdsSerializer,
    SkillBulkImportSerializer,
    SkillChangeStatusSerializer,
    SkillDropdownSerializer,
    SkillImportBatchSerializer,
    SkillImportErrorSerializer,
    SkillSerializer,
)
from skill.services import skill_service
from utils.custom_filters import CustomSearchFilter
from utils.pagination import Pagination
from utils.cache_keys import dropdown_key


class SkillViewSet(ModelViewSet):
    serializer_class = SkillSerializer
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = ["skill_code", "skill_name", "description"]
    ordering_fields = [
        "skill_code",
        "skill_name",
        "skill_type",
        "created_at",
        "updated_at",
    ]
    permission_classes = [SkillMasterPermission]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        qs = skill_service.skill_base_queryset()
        act = getattr(self, "action", None)
        if act == "archived":
            return qs.filter(deleted=True).order_by("-updated_at", "-created_at")
        return qs.filter(deleted=False).order_by("-created_at")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        req = self.request.query_params
        if "is_active" in req:
            v = str(req.get("is_active")).lower()
            if v in ("true", "1", "yes"):
                queryset = queryset.filter(is_active=True)
            elif v in ("false", "0", "no"):
                queryset = queryset.filter(is_active=False)
        skill_type = req.get("skill_type")
        if skill_type not in (None, ""):
            queryset = queryset.filter(skill_type=str(skill_type).strip().lower())
        return queryset

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            UUID(str(pk))
        except (ValueError, TypeError):
            raise NotFound()
        qs = skill_service.skill_base_queryset().filter(deleted=False)
        try:
            return qs.get(pk=pk)
        except Skill.DoesNotExist:
            raise NotFound()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Skill created", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response({"success": False, "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            skill_service.soft_archive_skill(skill=instance, user=request.user)
        except ValidationError as e:
            return Response({"success": False, "message": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "message": "Archived Successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="archived")
    def archived(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = SkillSerializer(queryset, many=True, context={"request": request})
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = SkillSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = SkillSerializer(queryset, many=True, context={"request": request})
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        ser = SkillChangeStatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"success": False, "message": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        skill_service.set_active_status(
            skill=instance,
            user=request.user,
            is_active=ser.validated_data["is_active"],
        )
        instance.refresh_from_db()
        return Response(
            {
                "success": True,
                "data": SkillSerializer(instance, context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request, *args, **kwargs):
        skill_type = request.query_params.get("skill_type")
        key = dropdown_key("skills") if not skill_type else f"{dropdown_key('skills')}:skill_type:{str(skill_type).strip().lower()}"
        try:
            cached = cache.get(key)
        except Exception:
            cached = None
        if cached is not None:
            return Response({"success": True, "data": cached})

        qs = skill_service.dropdown_skills()
        if skill_type not in (None, ""):
            qs = qs.filter(skill_type=str(skill_type).strip().lower())
        serializer = SkillDropdownSerializer(qs, many=True)
        data = serializer.data
        try:
            cache.set(key, data, 60 * 60)
        except Exception:
            pass
        return Response({"success": True, "data": data})

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        ser = SkillBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"success": False, "message": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            n = skill_service.bulk_archive(ids=list(ser.validated_data["ids"]), user=request.user)
        except ValidationError as e:
            return Response({"success": False, "message": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "message": "Bulk archived successfully", "count": n})

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        ser = SkillBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"success": False, "message": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        n = skill_service.bulk_restore(ids=list(ser.validated_data["ids"]), user=request.user)
        return Response({"success": True, "message": "Bulk restored successfully", "count": n})

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request, *args, **kwargs):
        ser = SkillBulkImportSerializer(data=request.data)
        if not ser.is_valid():
            return Response({"success": False, "message": ser.errors}, status=status.HTTP_400_BAD_REQUEST)
        batch = skill_service.bulk_import_rows(
            user=request.user,
            rows=ser.validated_data["rows"],
            serializer_class=SkillSerializer,
            context={"request": request},
        )
        return Response(
            {
                "success": True,
                "data": SkillImportBatchSerializer(batch, context={"request": request}).data,
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
        rows, parse_errors = skill_service.parse_import_file(upload)
        if not rows:
            msg = parse_errors or ["No data rows in file."]
            return Response({"success": False, "message": msg}, status=status.HTTP_400_BAD_REQUEST)
        result = skill_service.bulk_import_skills(
            user=request.user,
            rows=rows,
            serializer_class=SkillSerializer,
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
        qs = skill_service.import_batches_queryset()
        page = self.paginate_queryset(qs)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = SkillImportBatchSerializer(qs, many=True, context={"request": request})
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = SkillImportBatchSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = SkillImportBatchSerializer(qs, many=True, context={"request": request})
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="import-errors")
    def import_errors(self, request, *args, **kwargs):
        batch_id = request.query_params.get("batch_id")
        bid = None
        if batch_id:
            try:
                bid = UUID(str(batch_id))
            except (ValueError, TypeError):
                return Response({"success": False, "message": "Invalid batch_id"}, status=status.HTTP_400_BAD_REQUEST)
        qs = skill_service.import_errors_queryset(batch_id=bid)
        page = self.paginate_queryset(qs)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = SkillImportErrorSerializer(qs, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = SkillImportErrorSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = SkillImportErrorSerializer(qs, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="error-report/download")
    def error_report_download(self, request, *args, **kwargs):
        batch_id = request.query_params.get("batch_id")
        bid = None
        if batch_id:
            try:
                bid = UUID(str(batch_id))
            except (ValueError, TypeError):
                return Response({"success": False, "message": "Invalid batch_id"}, status=status.HTTP_400_BAD_REQUEST)
        filename, data = skill_service.error_report_csv_bytes(batch_id=bid)
        resp = HttpResponse(data, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

