from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from activity_log.models import ActivityLog
from city_areas.models import CityArea
from city_areas.serializers import (
    CityAreaArchiveListSerializer,
    CityAreaArchiveSerializer,
    CityAreaRestoreSerializer,
    CityAreaSerializer,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class CityAreaViewSet(ModelViewSet):
    queryset = CityArea.objects.filter(deleted=False).order_by("-id")
    serializer_class = CityAreaSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "city_area_name",
        "country__name",
        "state__name",
        "city__name",
        "zipcode",
    ]

    ordering_fields = [
        "id",
        "city_area_name",
        "country__id",
        "country__name",
        "state__id",
        "state__name",
        "city__id",
        "city__name",
        "zipcode",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = CityArea.objects.filter(deleted=False).select_related("country", "state", "city")

        city_id = self.request.query_params.get("city_id", None)
        if city_id:
            queryset = queryset.filter(city_id=city_id)

        city_name = self.request.query_params.get("city_name", None)
        if city_name:
            queryset = queryset.filter(city__name__icontains=city_name)

        state_id = self.request.query_params.get("state_id", None)
        if state_id:
            queryset = queryset.filter(state_id=state_id)

        state_name = self.request.query_params.get("state_name", None)
        if state_name:
            queryset = queryset.filter(state__name__icontains=state_name)

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
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                instance = serializer.save()
                ip_address = get_client_ip(request)
                ActivityLog.log.city_area_create(instance, ip_address, request.user)
                return Response(
                    {"success": True, "message": "City Area added successfully", "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            else:
                error_message = serializer.errors
                if isinstance(error_message, dict) and "non_field_errors" in error_message:
                    error_message = error_message["non_field_errors"][0]
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {"success": False, "message": "City Area already exists or database error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"success": True, "data": serializer.data})

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        try:
            if serializer.is_valid():
                instance = serializer.save()
                ip_address = get_client_ip(request)
                ActivityLog.log.city_area_update(instance, ip_address, request.user)
                return Response(
                    {"success": True, "message": "City Area updated successfully", "data": serializer.data},
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                error_message = serializer.errors
                if isinstance(error_message, dict) and "non_field_errors" in error_message:
                    error_message = error_message["non_field_errors"][0]
                return Response(
                    {"success": False, "message": error_message},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception:
            return Response(
                {"success": False, "message": "City Area already exists or database error occurred"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        ip_address = get_client_ip(request)
        ActivityLog.log.city_area_archive(instance, ip_address, request.user)
        instance.save()
        return Response(
            {"success": True, "message": "City Area Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(detail=False, methods=["GET"], url_path="city-area-list", permission_classes=[], authentication_classes=[])
    def city_area_list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).order_by("city_area_name")
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


# City Area Delete ViewSet
class CityAreaArchiveViewSet(ModelViewSet):
    queryset = CityArea.objects.filter(deleted=True).order_by("-id")
    serializer_class = CityAreaSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "city_area_name",
        "country__name",
        "state__name",
        "city__name",
        "zipcode",
    ]

    ordering_fields = [
        "id",
        "city_area_name",
        "country__id",
        "country__name",
        "state__id",
        "state__name",
        "city__id",
        "city__name",
        "zipcode",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        queryset = CityArea.objects.filter(deleted=True).select_related("country", "state", "city")

        state_id = self.request.query_params.get("state_id", None)
        if state_id:
            queryset = queryset.filter(state_id=state_id)

        state_name = self.request.query_params.get("state_name", None)
        if state_name:
            queryset = queryset.filter(state__name__icontains=state_name)

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
            serializer = CityAreaArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = CityAreaArchiveListSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = CityAreaArchiveListSerializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CityAreaArchiveSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.city_area_archive(instance, ip_address=ip_address, user=request.user)
            message = "City Area archived successfully" if count == 1 else "City Areas archived successfully"
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# City Area Archive ViewSet
class CityAreaRestoreViewSet(ModelViewSet):
    queryset = CityArea.objects.filter(deleted=True).order_by("-id")
    serializer_class = CityAreaSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = CityAreaRestoreSerializer(data=request.data)

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.city_area_restore(instance, user=request.user, ip_address=ip_address)
            message = "City Area restored successfully" if count == 1 else "City Areas restored successfully"
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
