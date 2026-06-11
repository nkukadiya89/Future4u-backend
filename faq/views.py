from django.utils import timezone
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from common.mixins.view_mixins import ListEnvelopeMixin, MethodNotAllowedListMixin
from faq.models import FAQ
from faq.serializers import (
    FAQArchiveListSerializer,
    FAQArchiveSerializer,
    FAQRestoreSerializer,
    FAQSerializers,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class FAQViewSet(ListEnvelopeMixin, ModelViewSet):
    queryset = FAQ.objects.filter(deleted=False).order_by("-id")
    serializer_class = FAQSerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "id",
        "question",
        "answer",
    ]

    ordering_fields = [
        "id",
        "question",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(created_by=request.user)
            ip_address = get_client_ip(request)
            ActivityLog.log.faq_create(instance, ip_address, request.user)
            return Response(
                {
                    "success": True,
                    "message": "FAQ added successfully",
                    "data": self.get_serializer(instance).data,
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
            instance = serializer.save(updated_by=request.user)
            instance.updated_at = timezone.now()
            instance.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.faq_update(instance, ip_address, request.user)
            return Response(
                {
                    "success": True,
                    "message": "FAQ updated successfully",
                    "data": self.get_serializer(instance).data,
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
        instance.deleted_by = request.user
        instance.deleted_at = timezone.now()
        instance.updated_by = request.user
        instance.updated_at = timezone.now()
        instance.save()
        ip_address = get_client_ip(request)
        ActivityLog.log.faq_archive(instance, ip_address, request.user)
        return Response(
            {"success": True, "message": "FAQ Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )


# FAQ Archive ViewSet
class FAQArchiveViewSet(ModelViewSet):
    queryset = FAQ.objects.filter(deleted=True).order_by("-id")
    serializer_class = FAQArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "id",
        "question",
        "answer",
    ]

    ordering_fields = [
        "id",
        "question",
        "created_at",
        "updated_at",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = FAQArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = FAQArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = FAQArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = FAQArchiveSerializer(
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
            ActivityLog.log.faq_archive(
                instance, ip_address=ip_address, user=request.user
            )
            message = (
                "FAQ archived successfully"
                if count == 1
                else "FAQs archived successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# FAQ Restore ViewSet
class FAQRestoreViewSet(MethodNotAllowedListMixin, ModelViewSet):
    queryset = FAQ.objects.filter(deleted=True).order_by("-id")
    serializer_class = FAQRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "id",
        "question",
        "answer",
    ]

    ordering_fields = [
        "id",
        "question",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = FAQRestoreSerializer(data=request.data)

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.faq_restore(
                instance, user=request.user, ip_address=ip_address
            )
            message = (
                "FAQ restored successfully"
                if count == 1
                else "FAQs restored successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
