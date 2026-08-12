from django.db.models import Count, Max, Sum
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.models import User
from user.permissions import IsAdminOrProvider, is_admin_user
from utils.datetime_formatter import format_datetime
from utils.token_check import (
    _check_org_monthly_reset,
    _get_org_profile,
    get_org_token_usage,
)
from user_profile.models import OrganizationTokenUsage


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


class OrganizationTokenUsageRowSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    organization = serializers.IntegerField(source="organization_id")
    user = serializers.IntegerField(source="user_id")
    feature_code = serializers.CharField()
    tokens_used = serializers.IntegerField()
    balance_after = serializers.IntegerField()
    created_at = serializers.DateTimeField()


def _current_cycle_usage(owner):
    profile = _get_org_profile(owner)
    if not profile:
        return 0
    qs = OrganizationTokenUsage.objects.filter(organization_id=owner.id)
    if profile.last_token_reset_at:
        qs = qs.filter(created_at__date__gte=profile.last_token_reset_at)
    return qs.aggregate(total=Sum("tokens_used"))["total"] or 0


def _get_staff_usage(owner, from_date=None, to_date=None):
    staff_ids = list(
        User.objects.filter(
            created_by=owner, is_org_staff=True, deleted=False
        ).values_list("id", flat=True)
    )
    if not staff_ids:
        return []

    qs = OrganizationTokenUsage.objects.filter(
        organization_id=owner.id, user_id__in=staff_ids
    )
    if from_date:
        qs = qs.filter(created_at__date__gte=from_date)
    if to_date:
        qs = qs.filter(created_at__date__lte=to_date)

    user_totals = qs.values("user_id").annotate(
        tokens_used=Sum("tokens_used"),
        requests=Count("id"),
        last_activity_at=Max("created_at"),
    )
    feature_totals = qs.values("user_id", "feature_code").annotate(
        tokens=Sum("tokens_used"),
        requests=Count("id"),
    )

    features_by_user = {}
    for row in feature_totals:
        features_by_user.setdefault(row["user_id"], []).append(
            {
                "feature_code": row["feature_code"],
                "tokens": row["tokens"] or 0,
                "requests": row["requests"],
            }
        )

    user_meta = {
        u["id"]: u
        for u in User.objects.filter(id__in=staff_ids).values(
            "id", "full_name", "email"
        )
    }

    rows = []
    for total in user_totals:
        user_id = total["user_id"]
        meta = user_meta.get(user_id, {})
        features = features_by_user.get(user_id, [])
        features.sort(key=lambda f: f["tokens"], reverse=True)
        last_activity = total["last_activity_at"]
        rows.append(
            {
                "user": user_id,
                "user_name": meta.get("full_name") or "",
                "user_email": meta.get("email") or "",
                "tokens_used": total["tokens_used"] or 0,
                "requests": total["requests"],
                "last_activity_at": (
                    format_datetime(last_activity) if last_activity else None
                ),
                "features": features,
            }
        )

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

            usage = get_org_token_usage(profile, user.user_type)
            used_tokens = _current_cycle_usage(user)
            monthly_limit = usage["monthly_limit"]
            usage_percentage = (
                round((used_tokens / monthly_limit) * 100, 1)
                if monthly_limit > 0
                else 0
            )

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
                    "monthly_limit": usage["monthly_limit"],
                    "used_tokens": used_tokens,
                    "remaining_tokens": usage["remaining_tokens"],
                    "usage_percentage": usage_percentage,
                }
            )

        page = self.paginate_queryset(rows)
        serializer = self.get_serializer(page or rows, many=True)
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
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
            groups.append(
                {
                    "owner": {
                        "id": owner.id,
                        "organization": org_name,
                        "user_type": owner.user_type,
                    },
                    "staff": staff_rows,
                }
            )

        groups.sort(
            key=lambda g: sum(s["tokens_used"] for s in g["staff"]), reverse=True
        )

        page = self.paginate_queryset(groups)
        serializer = StaffUsageGroupSerializer(page or groups, many=True)
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="usage-rows")
    def usage_rows(self, request, *args, **kwargs):
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

        if is_admin_user(request.user):
            qs = OrganizationTokenUsage.objects.all()
        else:
            qs = OrganizationTokenUsage.objects.filter(organization_id=request.user.id)

        if from_date:
            qs = qs.filter(created_at__date__gte=parse_date(from_date))
        if to_date:
            qs = qs.filter(created_at__date__lte=parse_date(to_date))

        qs = qs.order_by("-created_at", "-id")

        page = self.paginate_queryset(qs)
        serializer = OrganizationTokenUsageRowSerializer(
            page if page is not None else qs, many=True
        )
        if page is not None:
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        return Response({"success": True, "data": serializer.data})
