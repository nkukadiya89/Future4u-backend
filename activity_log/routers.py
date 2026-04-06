from rest_framework.routers import DefaultRouter
from activity_log.views import ActivityLogViewSet

activity_log_router = DefaultRouter()
activity_log_router.register(
    "activity-log", ActivityLogViewSet, basename="activity_log"
)
