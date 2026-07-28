from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import User
from user.permissions import IsAdminOrProvider, is_admin_user
from utils.token_check import (
    _check_org_monthly_reset,
    _get_org_profile,
    get_org_token_usage,
)


class OrganizationTokenUsageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    user = serializers.IntegerField()
    organization = serializers.CharField()
    login_type = serializers.CharField()
    status = serializers.CharField()
    monthly_limit = serializers.IntegerField()
    used_tokens = serializers.IntegerField()
    remaining_tokens = serializers.IntegerField()
    usage_percentage = serializers.FloatField()


class OrganizationTokenUsageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
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
        if is_admin_user(self.request.user):
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

            user_id = self.request.query_params.get("user")
            if user_id:
                qs = qs.filter(id=user_id)

            profile_id = self.request.query_params.get("id")
            if profile_id:
                qs = qs.filter(
                    Q(school_college_profile__id=profile_id)
                    | Q(institute_profile__id=profile_id)
                    | Q(corporate_profile__id=profile_id)
                )

            return qs.select_related(
                "school_college_profile",
                "institute_profile",
                "corporate_profile",
            )

        return User.objects.filter(
            id=self.request.user.id,
            user_type__in=[
                User.Role.SCHOOL_COLLEGE,
                User.Role.INSTITUTE,
                User.Role.CORPORATE,
            ],
            deleted=False,
        ).select_related(
            "school_college_profile",
            "institute_profile",
            "corporate_profile",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        rows = []
        for user in page or queryset:
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

            rows.append(
                {
                    "id": profile.id,
                    "user": user.id,
                    "organization": org_name,
                    "login_type": user.user_type,
                    "status": user.status or "pending",
                    "monthly_limit": usage["monthly_limit"],
                    "used_tokens": usage["used_tokens"],
                    "remaining_tokens": usage["remaining_tokens"],
                    "usage_percentage": usage["usage_percentage"],
                }
            )

        serializer = self.get_serializer(rows, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({"success": True, "data": serializer.data})
