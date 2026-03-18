from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from bulk_upload.bulk_upload import Pincode_BulkUpload
from pincode.models import PinCode
from pincode.serializer import (
    PinCodeArchiveSerializer,
    PinCodeDeleteSerializer,
    PinCodeSerializer,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class PinCodeViewSet(ModelViewSet):
    queryset = PinCode.objects.filter(deleted=0).order_by("-id")
    serializer_class = PinCodeSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    ordering_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")

        pincode_number = request.query_params.get("search_pincode_number")

        if pincode_number and len(pincode_number) >= 4:
            queryset = PinCode.objects.filter(
                pincode_number__startswith=pincode_number, deleted=0
            ).order_by("pincode_number")
            serializer = self.serializer_class(queryset, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

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
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.pincode_create(instance, ip_address, request.user)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            errors_message = " ".join(
                [", ".join(value) for value in serializer.errors.values()]  # type: ignore
            )
            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            ActivityLog.log.pincode_update(instance, request.user)

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            errors_message = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Pincode Deleted"}, status=status.HTTP_200_OK
        )


# Pincode Multiple Delete
class PinCodeDeleteViewSet(ModelViewSet):
    queryset = PinCode.objects.filter(deleted=0).order_by("-id")
    serializer_class = PinCodeSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    ordering_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    def create(self, request, *args, **kwargs):
        serializer = PinCodeDeleteSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            ActivityLog.log.pincode_archive(instance, request.user)

            return Response(
                {"success": True, "message": "Pincode archive Succefully"},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Pincode Multiple Archive
class PinCodeArchiveViewSet(ModelViewSet):
    queryset = PinCode.objects.filter(deleted=1).order_by("-id")
    serializer_class = PinCodeSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    search_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    ordering_fields = [
        "zone_id__zone_name",
        "pincode_number",
        "city_name",
        "state_name",
    ]

    def create(self, request, *args, **kwargs):
        serializer = PinCodeArchiveSerializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save()
            ActivityLog.log.pincode_restore(instance, request.user)
            return Response(
                {"success": True, "message": "Multiple Catergory restore Succefully"},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PinCodeBulkImportViewSet(ModelViewSet):
    queryset = PinCode.objects.filter(deleted=0).order_by("-id")
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        upload_file = request.data["upload_file"]

        if upload_file:
            bulk_upload = Pincode_BulkUpload(upload_file=upload_file)
            value = bulk_upload.process_pincode_csv(created_by=request.user.id)
            return Response(value)
        else:
            return Response(
                {"message": "File not found", "status": status.HTTP_404_NOT_FOUND}
            )
