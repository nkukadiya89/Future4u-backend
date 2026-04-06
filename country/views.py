from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from country.models import Country
from country.serializers import (
    CountryArchiveListSerializer,
    CountryArchiveSerializer,
    CountryRestoreSerializer,
    CountrySerializers,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class CountryViewSet(ModelViewSet):
    queryset = Country.objects.filter(deleted=False).order_by("-id")
    serializer_class = CountrySerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "id",
        "name",
        "code",
        "unicode",
        "country_flag",
    ]

    ordering_fields = [
        "id",
        "name",
        "code",
        "unicode",
        "country_flag",
        "created_at",
        "updated_at",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CountrySerializers(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CountrySerializers(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.country_create(instance, ip_address, request.user)
            return Response(
                {
                    "success": True,
                    "message": "Country added successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.country_update(instance, ip_address, request.user)
            return Response(
                {
                    "success": True,
                    "message": "Country updated successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        ip_address = get_client_ip(request)
        ActivityLog.log.country_archive(instance, ip_address, request.user)
        instance.save()
        return Response(
            {"success": True, "message": "Country Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=False,
        methods=["GET"],
        url_path="country-list",
        permission_classes=[],
        authentication_classes=[],
    )
    def country_list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CountrySerializers(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CountrySerializers(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


# Country Archive ViewSet
class CountryArchiveViewSet(ModelViewSet):
    queryset = Country.objects.filter(deleted=True).order_by("-id")
    serializer_class = CountryArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "id",
        "name",
        "code",
        "unicode",
        "country_flag",
    ]

    ordering_fields = [
        "id",
        "name",
        "code",
        "unicode",
        "country_flag",
        "created_at",
        "updated_at",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = CountryArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = CountryArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CountryArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CountryArchiveSerializer(
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
            ActivityLog.log.country_archive(
                instance, ip_address=ip_address, user=request.user
            )
            message = (
                "Country archived successfully"
                if count == 1
                else "Countries archived successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Country Restore ViewSet
class CountryRestoreViewSet(ModelViewSet):
    queryset = Country.objects.filter(deleted=True).order_by("-id")
    serializer_class = CountryRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = CountryRestoreSerializer(data=request.data)

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.country_restore(
                instance, user=request.user, ip_address=ip_address
            )
            message = (
                "Country restored successfully"
                if count == 1
                else "Countries restored successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
