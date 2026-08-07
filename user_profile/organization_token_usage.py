from datetime import datetime, time as dt_time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from activity_log.models import ActivityLog
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
    monthly_limit = serializers.IntegerField()
    used_tokens = serializers.IntegerField()
    remaining_tokens = serializers.IntegerField()
    usage_percentage = serializers.FloatField()


class StaffUsageFeatureSerializer(serializers.Serializer):
    feature_code = serializers.CharField()
    tokens = serializers.IntegerField()
    requests = serializers.IntegerField()


class StaffUsageSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    user_name = serializers.CharField()
    user_email = serializers.CharField()
    tokens_used = serializers.IntegerField()
    requests = serializers.IntegerField()
    last_activity_at = serializers.CharField(allow_null=True)
    features = StaffUsageFeatureSerializer(many=True)


class StaffUsageOwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    organization = serializers.CharField()
    user_type = serializers.CharField()


class StaffUsageGroupSerializer(serializers.Serializer):
    owner = StaffUsageOwnerSerializer()
    staff = StaffUsageSerializer(many=True)


def _get_staff_usage(owner, from_date=None, to_date=None):
    staff_ids = User.objects.filter(
        created_by=owner, is_org_staff=True, deleted=False
    ).values_list("id", flat=True)

    logs = ActivityLog.objects.filter(
        event="user.tokens_deducted",
        entity_type="user",
        entity_id=owner.id,
        user_id__in=staff_ids,
    )
    if from_date:
        start = timezone.make_aware(datetime.combine(from_date, dt_time.min))
        logs = logs.filter(created_at__gte=start)
    if to_date:
        end = timezone.make_aware(
            datetime.combine(to_date + timedelta(days=1), dt_time.min)
        )
        logs = logs.filter(created_at__lt=end)

    rows_by_user = {}
    for log in logs.select_related("user").order_by("created_at"):
        entry = rows_by_user.setdefault(
            log.user_id,
            {
                "user": log.user_id,
                "user_name": getattr(log.user, "full_name", None) or "",
                "user_email": getattr(log.user, "email", None) or "",
                "tokens_used": 0,
                "requests": 0,
                "last_activity_at": None,
                "features": {},
            },
        )
        feature_code = log.metadata.get("feature_code") or "unknown"
        feature = entry["features"].setdefault(
            feature_code,
            {"feature_code": feature_code, "tokens": 0, "requests": 0},
        )
        tokens = log.metadata.get("tokens") or 0
        feature["tokens"] += tokens
        feature["requests"] += 1
        entry["tokens_used"] += tokens
        entry["requests"] += 1
        entry["last_activity_at"] = log.created_at

    rows = []
    for entry in rows_by_user.values():
        entry["features"] = sorted(
            entry["features"].values(), key=lambda f: f["tokens"], reverse=True
        )
        entry["last_activity_at"] = (
            entry["last_activity_at"].isoformat()
            if entry["last_activity_at"]
            else None
        )
        rows.append(entry)

    rows.sort(key=lambda r: r["tokens_used"], reverse=True)
    return rows


class OrganizationTokenUsageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    serializer_class = OrganizationTokenUsageSerializer
    filter_backends = [SearchFilter]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "school_college_profile__institute_name",
        "institute_profile__institute_name",
        "corporate_profile__company_name",
    ]

    def get_queryset(self):
        if is_admin_user(self.request.user):
            qs = User.objects.filter(
                user_type__in=[
                    User.Role.SCHOOL_COLLEGE,
                    User.Role.INSTITUTE,
                    User.Role.CORPORATE,
                ],
                is_org_staff=False,
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

        return User.objects.filter(
            id=self.request.user.id,
            user_type__in=[
                User.Role.SCHOOL_COLLEGE,
                User.Role.INSTITUTE,
                User.Role.CORPORATE,
            ],
            is_org_staff=False,
            deleted=False,
        ).select_related(
            "school_college_profile",
            "institute_profile",
            "corporate_profile",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        rows = []
        for user in queryset:
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
                "id": profile.id,
                "user": user.id,
                "organization": org_name,
                "login_type": user.user_type,
                "monthly_limit": usage["monthly_limit"],
                "used_tokens": usage["used_tokens"],
                "remaining_tokens": usage["remaining_tokens"],
                "usage_percentage": usage["usage_percentage"],
            })

        page = self.paginate_queryset(rows)
        serializer = self.get_serializer(page or rows, many=True)
        if page is not None:
            return self.get_paginated_response({"success": True, "data": serializer.data})
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="staff-usage")
    def staff_usage(self, request, *args, **kwargs):
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        if from_date and not parse_date(from_date):
            return Response(
                {"success": False, "message": "from_date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if to_date and not parse_date(to_date):
            return Response(
                {"success": False, "message": "to_date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        owners = self.filter_queryset(self.get_queryset())

        groups = []
        for owner in owners:
            staff_rows = _get_staff_usage(
                owner,
                from_date=parse_date(from_date) if from_date else None,
                to_date=parse_date(to_date) if to_date else None,
            )
            if not staff_rows:
                continue
            profile = _get_org_profile(owner)
            org_name = (
                getattr(profile, "institute_name", None)
                or getattr(profile, "company_name", None)
                or ""
            )
            groups.append({
                "owner": {
                    "id": owner.id,
                    "organization": org_name,
                    "user_type": owner.user_type,
                },
                "staff": staff_rows,
            })

        groups.sort(
            key=lambda g: sum(s["tokens_used"] for s in g["staff"]), reverse=True
        )

        page = self.paginate_queryset(groups)
        serializer = StaffUsageGroupSerializer(page or groups, many=True)
        if page is not None:
            return self.get_paginated_response({"success": True, "data": serializer.data})
        return Response({"success": True, "data": serializer.data})
