from datetime import datetime, time as dt_time, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from activity_log.serializers import ActivityLogSerializer
from utils.pagination import Pagination


class ActivityLogViewSet(ReadOnlyModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    filter_backends = [SearchFilter]
    pagination_class = Pagination
    search_fields = ["event", "description", "user__email", "user__full_name"]

    def get_queryset(self):
        user = self.request.user
        qs = ActivityLog.objects.select_related("user").order_by("-created_at")

        if (
            not user.is_superuser
            and not getattr(user, "user_type", None) == "super_admin"
        ):
            qs = qs.filter(user=user)

        event = self.request.query_params.get("event")
        if event:
            qs = qs.filter(event=event)

        from_date = self.request.query_params.get("from_date")
        if from_date:
            parsed = parse_date(from_date)
            if parsed:
                start = timezone.make_aware(datetime.combine(parsed, dt_time.min))
                qs = qs.filter(created_at__gte=start)

        to_date = self.request.query_params.get("to_date")
        if to_date:
            parsed = parse_date(to_date)
            if parsed:
                end = timezone.make_aware(
                    datetime.combine(parsed + timedelta(days=1), dt_time.min)
                )
                qs = qs.filter(created_at__lt=end)

        return qs

    def list(self, request, *args, **kwargs):
        from_date = request.query_params.get("from_date")
        if from_date and not parse_date(from_date):
            return Response(
                {"success": False, "message": "from_date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        to_date = request.query_params.get("to_date")
        if to_date and not parse_date(to_date):
            return Response(
                {"success": False, "message": "to_date must be YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.serializer_class(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        qs = (
            ActivityLog.objects.filter(user=request.user)
            .select_related("user")
            .order_by("-created_at")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = self.serializer_class(qs, many=True)
        return Response({"success": True, "data": serializer.data})
