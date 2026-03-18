from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from country.models import Country
from country.serializers import CountrySerializers
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class CountryViewSet(ModelViewSet):
    queryset = Country.objects.filter(deleted=0).order_by("-id")
    serializer_class = CountrySerializers
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "name",
        "code",
        "unicode",
        "country_flag",
    ]

    ordering_fields = [
        "name",
        "code",
        "unicode",
        "country_flag",
    ]

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
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            instance = serializer.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.country_create(instance, ip_address, request.user)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            ActivityLog.log.country_update(instance, request.user)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_202_ACCEPTED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        ActivityLog.log.country_archive(instance, request.user)
        instance.save()
        return Response(
            {"success": True, "message": "Country Deleted"},
            status=status.HTTP_204_NO_CONTENT,
        )
