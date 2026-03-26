from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from activity_log.models import ActivityLog
from common.api.mixins import ArchiveMixin
from business_category.models import BusinessCategory
from business_category.serializers import (
    # BusinessCategoryArchiveListSerializer,
    # BusinessCategoryArchiveSerializer,
    # BusinessCategoryRestoreSerializer,
    BusinessCategorySerializers,
    BusinessCategoryDropdownSerializer
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination
from common.master_view import BaseModelViewSet


class BusinessCategoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = BusinessCategory.objects.all().order_by("-id")
    serializer_class = BusinessCategorySerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = BaseModelViewSet.searching_fields +["=id", "business_category"]
    ordering_fields = BaseModelViewSet.ordering_fields +["id", "business_category"]

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

        if serializer.is_valid():
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.business_category_create(instance, ip_address, request.user)
            return Response(
                {"success": True, "message": "Business category added successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.business_category_update(instance, ip_address, request.user)
            return Response(
                {"success": True, "message": "Business category updated successfully", "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if getattr(instance, "deleted", False):
            return Response({"success": False, "message": "Already Archived"}, status=status.HTTP_400_BAD_REQUEST)
        instance.deleted = 1
        instance.deleted_at = timezone.now()
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        instance.save()
        ip_address = get_client_ip(request)
        ActivityLog.log.business_category_archive(instance, ip_address, request.user)
        return Response(
            {"success": True, "message": "Business category Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )
        
    @action(
        detail=False,
        methods=["get"],
        url_path="category",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def get_category(self, request, *args, **kwargs):
        queryset = BusinessCategory.objects.filter(deleted=False).order_by("-id").values("id", "business_category")
        return Response({"success": True, "data": list(queryset)})


    @action(detail=False, methods=["get"], url_path="dropdown")
    def dropdown(self, request):
        queryset = BusinessCategory.objects.filter(deleted=False)

        filter_param = request.query_params.get("filter")
        if filter_param:
            queryset = queryset.filter(name__icontains=filter_param) | queryset.filter(
                code__icontains=filter_param
            )

        serializer = BusinessCategoryDropdownSerializer(queryset, many=True)
        return Response(
            {"success": True, "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class BusinessCategoryArchiveViewSet(ModelViewSet):
    """
    Dedicated endpoints to match existing test/URL naming:
    - `business_category_archive-list` GET: list archived
    - `business_category_archive-list` POST: bulk archive
    """

    queryset = BusinessCategory.objects.all().order_by("-id")
    serializer_class = BusinessCategorySerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination

    def get_queryset(self):
        return super().get_queryset().filter(deleted=True).order_by("-id")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.get_serializer(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        ids = request.data.get("deleted", [])
        if not ids:
            return Response({"success": False, "message": "Ids are Required"}, status=status.HTTP_400_BAD_REQUEST)
        qs = BusinessCategory.objects.filter(id__in=ids, deleted=False)
        if not qs.exists():
            return Response({"success": False, "message": "No valid ids"}, status=status.HTTP_400_BAD_REQUEST)
        qs.update(deleted=True, deleted_at=timezone.now(), deleted_by=request.user)
        ip_address = get_client_ip(request)
        ActivityLog.log.business_category_archive(qs.first(), ip_address, request.user)
        return Response(
            {"success": True, "message": "Business categories archived successfully"},
            status=status.HTTP_200_OK,
        )


class BusinessCategoryRestoreViewSet(ModelViewSet):
    """
    Dedicated endpoint to match existing test/URL naming:
    - `business_category_restore-list` POST: bulk restore
    GET is not allowed (405), as expected by tests.
    """

    queryset = BusinessCategory.objects.all().order_by("-id")
    serializer_class = BusinessCategorySerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    http_method_names = ["post", "head", "options"]

    def create(self, request, *args, **kwargs):
        ids = request.data.get("deleted", [])
        if not ids:
            return Response({"success": False, "message": "Ids are Required"}, status=status.HTTP_400_BAD_REQUEST)
        qs = BusinessCategory.objects.filter(id__in=ids, deleted=True)
        if not qs.exists():
            return Response({"success": False, "message": "No valid ids"}, status=status.HTTP_400_BAD_REQUEST)
        qs.update(deleted=False, deleted_at=None, deleted_by=None)
        ip_address = get_client_ip(request)
        ActivityLog.log.business_category_restore(qs.first(), ip_address, request.user)
        return Response(
            {"success": True, "message": "Business category restored successfully"},
            status=status.HTTP_200_OK,
        )