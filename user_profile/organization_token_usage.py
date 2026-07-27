from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from user.models import User
from user.permissions import IsAdminUser
from utils.token_check import (
    _check_org_monthly_reset,
    _get_org_profile,
    get_org_token_usage,
)


class OrganizationTokenUsageSerializer(serializers.Serializer):
    organization = serializers.CharField()
    login_type = serializers.CharField()
    status = serializers.CharField()
    monthly_limit = serializers.IntegerField()
    used_tokens = serializers.IntegerField()
    remaining_tokens = serializers.IntegerField()
    usage_percentage = serializers.FloatField()


class OrganizationTokenUsageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = OrganizationTokenUsageSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "school_college_profile__institute_name",
        "institute_profile__institute_name",
        "corporate_profile__company_name",
    ]
    ordering_fields = [
        "user_type",
        "status",
        "school_college_profile__token_limit",
        "institute_profile__token_limit",
        "corporate_profile__token_limit",
    ]

    def get_queryset(self):
        qs = User.objects.filter(
            user_type__in=[
                User.Role.SCHOOL_COLLEGE,
                User.Role.INSTITUTE,
                User.Role.CORPORATE,
            ],
            deleted=False,
        )
        user_type = self.request.query_params.get("user_type")
        if user_type:
            qs = qs.filter(user_type=user_type)
        return qs.select_related(
            "school_college_profile",
            "institute_profile",
            "corporate_profile",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        rows = []
        for user in (page or queryset):
            profile = _get_org_profile(user)
            if not profile:
                continue

            _check_org_monthly_reset(profile, user.user_type)

            usage = get_org_token_usage(profile, user.user_type)

            org_name = (
                getattr(profile, "institute_name", None)
                or getattr(profile, "company_name", None)
                or ""
            )

            rows.append({
                "organization": org_name,
                "login_type": user.user_type,
                "status": user.status or "pending",
                "monthly_limit": usage["monthly_limit"],
                "used_tokens": usage["used_tokens"],
                "remaining_tokens": usage["remaining_tokens"],
                "usage_percentage": usage["usage_percentage"],
            })

        serializer = self.get_serializer(rows, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "data": serializer.data})
