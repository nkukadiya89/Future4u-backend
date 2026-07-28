from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from common.mixins.view_mixins import SuccessEnvelopeMixin
from language_master.models import Language
from language_master.permissions import LanguageMasterPermission
from language_master.serializers import (
    LanguageBulkIdsSerializer,
    LanguageChangeStatusSerializer,
    LanguageDropdownSerializer,
    LanguageImportBatchSerializer,
    LanguageSerializer,
)
from language_master.services import language_service
from utils.pagination import Pagination


class LanguageViewSet(SuccessEnvelopeMixin, ModelViewSet):
    list_unpaginated_fallback = True
    serializer_class = LanguageSerializer
    pagination_class = Pagination
    filter_backends = [OrderingFilter]
    ordering_fields = ["name", "code", "created_at"]
    permission_classes = [LanguageMasterPermission]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        qs = language_service.language_base_queryset()
        if getattr(self, "action", None) == "archived":
            return qs.filter(deleted=True).order_by("-updated_at")
        return qs.filter(deleted=False).order_by("name")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        req = self.request.query_params
        if "is_active" in req:
            v = str(req.get("is_active")).lower()
            if v in ("true", "1", "yes"):
                queryset = queryset.filter(is_active=True)
            elif v in ("false", "0", "no"):
                queryset = queryset.filter(is_active=False)
        return queryset

    def get_object(self):
        pk = self.kwargs.get("pk")
        try:
            UUID(str(pk))
        except (ValueError, TypeError):
            raise NotFound()
        try:
            return (
                language_service.language_base_queryset()
                .filter(deleted=False)
                .get(pk=pk)
            )
        except Language.DoesNotExist:
            raise NotFound()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Language created",
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
        language_service.archive_language(language=instance, user=request.user)
        return Response(
            {"success": True, "message": "Archived successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request, *args, **kwargs):
        qs = language_service.dropdown_languages()
        return Response(
            {"success": True, "data": LanguageDropdownSerializer(qs, many=True).data}
        )

    @action(detail=False, methods=["get"], url_path="archived")
    def archived(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        ser = LanguageChangeStatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        language_service.set_active_status(
            language=instance,
            user=request.user,
            is_active=ser.validated_data["is_active"],
        )
        instance.refresh_from_db()
        return Response({"success": True, "data": self.get_serializer(instance).data})

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        ser = LanguageBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        n = language_service.bulk_archive(
            ids=list(ser.validated_data["ids"]), user=request.user
        )
        return Response({"success": True, "message": "Bulk archived", "count": n})

    @action(detail=False, methods=["post"], url_path="bulk-restore")
    def bulk_restore(self, request, *args, **kwargs):
        ser = LanguageBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        n = language_service.bulk_restore(
            ids=list(ser.validated_data["ids"]), user=request.user
        )
        return Response({"success": True, "message": "Bulk restored", "count": n})

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-upload",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_upload(self, request, *args, **kwargs):
        upload = request.FILES.get("file")
        rows, parse_errors = language_service.parse_import_file(upload)
        if not rows:
            return Response(
                {"success": False, "message": parse_errors or ["No data rows."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = language_service.bulk_import_languages(
            user=request.user,
            rows=rows,
            serializer_class=LanguageSerializer,
            context={"request": request},
        )
        return Response({**result, "success": True}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="import-logs")
    def import_logs(self, request, *args, **kwargs):
        qs = language_service.import_batches_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                {
                    "success": True,
                    "data": LanguageImportBatchSerializer(page, many=True).data,
                }
            )
        return Response(
            {"success": True, "data": LanguageImportBatchSerializer(qs, many=True).data}
        )

    @action(detail=False, methods=["get"], url_path="sample-csv")
    def sample_csv(self, request, *args, **kwargs):
        return language_service.sample_csv_http_response()
