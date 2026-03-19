from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.timezone import now
from activity_log.models import ActivityLog
from business_category.models import BusinessCategory
from business_category.serializers import (
    BusinessCategoryArchiveListSerializer,
    BusinessCategoryArchiveSerializer,
    BusinessCategoryRestoreSerializer,
    BusinessCategorySerializers,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class BusinessCategoryViewSet(ModelViewSet):
    queryset = BusinessCategory.objects.filter(deleted=False).order_by("-id")
    serializer_class = BusinessCategorySerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["=id", "=business_category"]

    ordering_fields = ["id", "business_category", "created_at", "updated_at"]

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
        instance.deleted = True
        instance.deleted_at = now()
        if hasattr(instance, "deleted_by"):
            instance.deleted_by = request.user
        ip_address = get_client_ip(request)
        ActivityLog.log.business_category_archive(instance, ip_address, request.user)
        instance.save()
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


# Business Category Archive ViewSet
class BusinessCategoryArchiveViewSet(ModelViewSet):
    queryset = BusinessCategory.objects.filter(deleted=True).order_by("-id")
    serializer_class = BusinessCategoryArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["=id", "=business_category"]

    ordering_fields = ["id", "business_category", "created_at", "updated_at"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = BusinessCategoryArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = BusinessCategoryArchiveListSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = BusinessCategoryArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = BusinessCategoryArchiveSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.business_category_archive(instance, ip_address=ip_address, user=request.user)
            message = (
                "Business category archived successfully" if count == 1 else "Business categories archived successfully"
            )
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Business Category Restore ViewSet
class BusinessCategoryRestoreViewSet(ModelViewSet):
    queryset = BusinessCategory.objects.filter(deleted=True).order_by("-id")
    serializer_class = BusinessCategoryRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["=id", "=business_category"]

    ordering_fields = ["id", "business_category", "created_at", "updated_at"]

    def list(self, request, *args, **kwargs):
        return Response({"success": False, "message": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request, *args, **kwargs):
        serializer = BusinessCategoryRestoreSerializer(data=request.data)

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.business_category_restore(instance, user=request.user, ip_address=ip_address)
            message = (
                "Business category restored successfully" if count == 1 else "Business categories restored successfully"
            )
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
