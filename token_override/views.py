from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.timezone import now

from common.mixins.view_mixins import ListEnvelopeMixin
from token_override.models import TokenOverride
from token_override.serializers import TokenOverrideSerializer
from utils.pagination import Pagination


class TokenOverrideViewSet(ListEnvelopeMixin, ModelViewSet):
    queryset = TokenOverride.objects.filter(deleted=False).order_by("-id")
    serializer_class = TokenOverrideSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "user__full_name",
        "user__email",
        "entity_type",
    ]
    ordering_fields = [
        "id",
        "user",
        "entity_type",
        "extra_monthly_tokens",
        "valid_until",
        "is_active",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self):
        qs = TokenOverride.objects.filter(deleted=False).select_related(
            "user", "created_by", "updated_by"
        )
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        user_id = self.request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(
                created_by=request.user,
                created_at=now(),
            )
            return Response(
                {
                    "success": True,
                    "message": "Token override created successfully",
                    "data": self.get_serializer(instance).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save(
                updated_by=request.user,
                updated_at=now(),
            )
            return Response(
                {
                    "success": True,
                    "message": "Token override updated successfully",
                    "data": self.get_serializer(instance).data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.deleted_at = now()
        instance.deleted_by = request.user
        instance.save(update_fields=["deleted", "deleted_at", "deleted_by"])
        return Response(
            {"success": True, "message": "Token override deleted"},
            status=status.HTTP_200_OK,
        )
