from uuid import UUID

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from stream_domain_mapping.models import StreamDomainMapping
from stream_domain_mapping.permissions import StreamDomainMappingPermission
from stream_domain_mapping.serializers import (
    StreamDomainMappingBulkIdsSerializer,
    StreamDomainMappingBulkImportSerializer,
    StreamDomainMappingChangeStatusSerializer,
    StreamDomainMappingSerializer,
)
from stream_domain_mapping.services import stream_domain_mapping_service
from utils.custom_filters import CustomSearchFilter
from utils.pagination import Pagination


class StreamDomainMappingViewSet(ModelViewSet):
    serializer_class = StreamDomainMappingSerializer
    pagination_class = Pagination
    filter_backends = [CustomSearchFilter, OrderingFilter]
    search_fields = ["stream__stream_name", "domain__domain_name"]
    ordering_fields = ["weight_score", "created_at", "updated_at"]
    permission_classes = [StreamDomainMappingPermission]
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        qs = stream_domain_mapping_service.mapping_base_queryset()
        if getattr(self, "action", None) == "archived":
            return qs.filter(deleted=True).order_by("-updated_at", "-created_at")
        return qs.filter(deleted=False).order_by("-weight_score")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        req = self.request.query_params
        stream_id = req.get("stream")
        if stream_id not in (None, ""):
            queryset = queryset.filter(stream_id=stream_id)
        domain_id = req.get("domain")
        if domain_id not in (None, ""):
            queryset = queryset.filter(domain_id=domain_id)
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
        qs = stream_domain_mapping_service.mapping_base_queryset().filter(deleted=False)
        try:
            return qs.get(pk=pk)
        except StreamDomainMapping.DoesNotExist:
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
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "success": True,
                    "message": "Stream-domain mapping created",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=False
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            stream_domain_mapping_service.archive_mapping(
                mapping=instance, user=request.user
            )
        except ValidationError as e:
            return Response(
                {"success": False, "message": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"success": True, "message": "Archived Successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None, *args, **kwargs):
        instance = self.get_object()
        ser = StreamDomainMappingChangeStatusSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stream_domain_mapping_service.set_active_status(
            mapping=instance,
            user=request.user,
            is_active=ser.validated_data["is_active"],
        )
        instance.refresh_from_db()
        return Response(
            {
                "success": True,
                "message": "Status updated",
                "data": StreamDomainMappingSerializer(
                    instance, context={"request": request}
                ).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="archived")
    def archived(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.get_serializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.get_serializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["post"], url_path="bulk-archive")
    def bulk_archive(self, request, *args, **kwargs):
        ser = StreamDomainMappingBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            n = stream_domain_mapping_service.bulk_archive(
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
        ser = StreamDomainMappingBulkIdsSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        n = stream_domain_mapping_service.bulk_restore(
            ids=list(ser.validated_data["ids"]), user=request.user
        )
        return Response(
            {"success": True, "message": "Bulk restored successfully", "count": n}
        )

    @action(detail=False, methods=["get"], url_path=r"by-stream/(?P<stream_id>[^/.]+)")
    def by_stream(self, request, stream_id=None, *args, **kwargs):
        qs = stream_domain_mapping_service.by_stream_queryset(stream_id=stream_id)
        serializer = self.get_serializer(qs, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(
        detail=False,
        methods=["post"],
        url_path="bulk-import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def bulk_import(self, request, *args, **kwargs):
        if "file" in request.FILES:
            rows, parse_errors = stream_domain_mapping_service.parse_import_file(
                request.FILES.get("file")
            )
            if not rows:
                return Response(
                    {
                        "success": False,
                        "success_count": 0,
                        "error_count": len(parse_errors),
                        "error_details": [
                            {"row": 0, "message": e} for e in parse_errors
                        ],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result = stream_domain_mapping_service.bulk_import_mappings(
                user=request.user,
                rows=rows,
                serializer_class=StreamDomainMappingSerializer,
                context={"request": request},
            )
            if parse_errors:
                result["error_details"] = result["error_details"] + [
                    {"row": 0, "message": e, "row_data": {}} for e in parse_errors
                ]
                result["error_count"] = len(result["error_details"])
            return Response({"success": True, **result}, status=status.HTTP_201_CREATED)

        ser = StreamDomainMappingBulkImportSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = stream_domain_mapping_service.bulk_import_mappings(
            user=request.user,
            rows=ser.validated_data["rows"],
            serializer_class=StreamDomainMappingSerializer,
            context={"request": request},
        )
        return Response({"success": True, **result}, status=status.HTTP_201_CREATED)
