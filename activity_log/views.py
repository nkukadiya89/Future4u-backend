from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from activity_log.serializers import ActivityLogSerializer
from utils import pagination
from utils.pagination import Pagination


class ActivityLogViewSet(ModelViewSet):
    queryset = ActivityLog.objects.all().order_by("-id")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset

        if hasattr(user, "company") and user.company:
            return queryset.filter(company=user.company)

        return queryset.filter(user=user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True, context={"request": request})
            return Response({"success": True, "data": serializer.data})

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="get-activity-log")
    def get_login_user_activity_log(self, request, *args, **kwargs):
        user = self.request.user

        activity_log_list = None
        if user.company:
            company_instance = user.company
            activity_log_list = ActivityLog.objects.filter(company=company_instance).order_by("-id")

        else:
            activity_log_list = ActivityLog.objects.all().order_by("-id")

        if activity_log_list is not None:
            # pagination = Pagination()
            result_page = pagination.paginate_queryset(activity_log_list, request)

            serializer = ActivityLogSerializer(result_page, many=True)
            return pagination.get_paginated_response({"success": True, "data": serializer.data})
        else:
            serializer = ActivityLogSerializer(activity_log_list, many=True)
            return Response({"success": True, "data": serializer.data})
