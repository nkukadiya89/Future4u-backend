from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination

from .models import State
from .serializers import (
    StateArchiveListSerializer,
    StateArchiveSerializer,
    StateRestoreSerializer,
    StateSerializer,
)


# Create your views here.
class StateViewSet(ModelViewSet):
    queryset = State.objects.filter(deleted=False).order_by("-id")
    serializer_class = StateSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["id", "name", "country__name"]

    ordering_fields = [
        "id",
        "name",
        "country__id",
        "country__name",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = State.objects.filter(deleted=False).select_related("country")

        country_id = self.request.query_params.get("country_id", None)
        if country_id:
            queryset = queryset.filter(country_id=country_id)

        country_name = self.request.query_params.get("country_name", None)
        if country_name:
            queryset = queryset.filter(country__name__icontains=country_name)

        return queryset.order_by("-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                instance = serializer.save()
                ip_address = get_client_ip(request)
                ActivityLog.log.state_create(instance, ip_address, request.user)
                return Response(
                    {
                        "success": True,
                        "message": "State created successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                error_message = serializer.errors
                if (
                    isinstance(error_message, dict)
                    and "non_field_errors" in error_message
                ):
                    error_message = error_message["non_field_errors"][0]
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "State name already exists or database error occurred",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = StateSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                instance = serializer.save()
                ip_address = get_client_ip(request)
                ActivityLog.log.state_update(instance, ip_address, request.user)
                return Response(
                    {
                        "success": True,
                        "message": "State updated successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                error_message = serializer.errors
                if (
                    isinstance(error_message, dict)
                    and "non_field_errors" in error_message
                ):
                    error_message = error_message["non_field_errors"][0]
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {
                    "success": False,
                    "message": "State name already exists or database error occurred",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()
        ip_address = get_client_ip(request)
        ActivityLog.log.state_archive(instance, ip_address, request.user)
        return Response(
            {"success": True, "message": "State Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=False,
        methods=["GET"],
        url_path="state-list",
        permission_classes=[],
        authentication_classes=[],
    )
    def state_list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).order_by("name")
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


class StateArchiveViewSet(ModelViewSet):
    queryset = State.objects.filter(deleted=True).order_by("-id")
    serializer_class = StateArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["id", "name", "country__name"]

    ordering_fields = [
        "id",
        "name",
        "country__id",
        "country__name",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = State.objects.filter(deleted=True).select_related("country")

        country_id = self.request.query_params.get("country_id", None)
        if country_id:
            queryset = queryset.filter(country_id=country_id)

        country_name = self.request.query_params.get("country_name", None)
        if country_name:
            queryset = queryset.filter(country__name__icontains=country_name)

        return queryset.order_by("-id")

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = StateArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = StateArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = StateArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = StateArchiveSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.state_archive(
                instance, ip_address=ip_address, user=request.user
            )
            message = (
                "State archived successfully"
                if count == 1
                else "States archived successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StateRestoreViewSet(ModelViewSet):
    queryset = State.objects.filter(deleted=True).order_by("-id")
    serializer_class = StateArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = StateRestoreSerializer(data=request.data)

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.state_restore(
                instance, ip_address=ip_address, user=request.user
            )
            message = (
                "State restored successfully"
                if count == 1
                else "States restored successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
