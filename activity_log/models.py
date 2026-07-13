from django.conf import settings
from django.db import models


class _NoOpLogger:
    """
    Backward-compatible no-op logger.
    Legacy ERP views still call ActivityLog.log.xxx_create(...) etc.
    This silently accepts any method call without doing anything.
    """

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    entity_type = models.CharField(max_length=100, null=True, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "activity_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["event", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event} - {self.created_at}"


# Backward-compatible no-op logger for legacy ERP views
ActivityLog.log = _NoOpLogger()
