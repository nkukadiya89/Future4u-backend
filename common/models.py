from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.timezone import now


# Create your models here.
class FinancialYearModel(models.Model):
    fid = models.AutoField(primary_key=True)
    financial_year = models.CharField(max_length=15, default="")
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(default=date.today)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fy_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    approved_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"({self.fid} )"

    class Meta:
        db_table = "financial_year"

    def get_current_financial_year(self):
        today = date.today()
        return FinancialYearModel.objects.filter(
            start_date__lte=today, end_date__gte=today, deleted=False
        ).first()


class BaseModule(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    @property
    def is_deleted(self):
        return self.deleted

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        if user is None and hasattr(self, "_request_user"):
            user = self._request_user

        update_fields = kwargs.get("update_fields")

        if self._state.adding:
            if user and not self.created_by:
                self.created_by = user
            self.updated_by = None
            self.updated_at = None
        else:
            if update_fields is None:
                if user:
                    self.updated_by = user
                if not self.deleted:
                    self.updated_at = timezone.now()
            else:
                if "updated_by" in update_fields and user:
                    self.updated_by = user
                if "updated_at" in update_fields and not self.deleted:
                    self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        self.deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        elif hasattr(self, "_request_user"):
            self.deleted_by = self._request_user
        super().save(update_fields=["deleted", "deleted_at", "deleted_by"])


"""
NOTE:
API/view concerns like ArchiveMixin should not live in models modules.
See `common/api/mixins.py`.
"""
