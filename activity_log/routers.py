from rest_framework.routers import DefaultRouter
from activity_log.views import ActivityLogViewSet, WhatsAppMessageLogViewSet

activity_log_router = DefaultRouter()
activity_log_router.register("activity-log", ActivityLogViewSet, basename="activity_log")
activity_log_router.register("whatsapp-message-log", WhatsAppMessageLogViewSet, basename="whatsapp_message_log")
