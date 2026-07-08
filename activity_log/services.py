import logging

from utils.generate_ip_address import get_client_ip

logger = logging.getLogger(__name__)


def log_event(
    event,
    description,
    user=None,
    entity_type=None,
    entity_id=None,
    metadata=None,
    request=None,
):
    """
    Create an ActivityLog entry. Safe to call from anywhere.
    Never raises — logs the error and continues if something goes wrong.
    """
    try:
        from activity_log.models import ActivityLog

        ActivityLog.objects.create(
            user=user,
            event=event,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata or {},
            ip_address=get_client_ip(request) if request else None,
        )
    except Exception as exc:
        logger.error("activity_log failed for event=%s: %s", event, exc)
