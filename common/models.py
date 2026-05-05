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
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)

    @property
    def is_deleted(self):
        return self.deleted

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        user = kwargs.pop("user", None)
        if is_new:
            # Don't set updated_at during creation
            self.updated_by = None
            if user and not self.created_by:
                self.created_by = user
        else:
            old_deleted = (
                getattr(self.__class__.objects.get(pk=self.pk), "deleted", False)
                if self.pk
                else False
            )
            current_deleted = getattr(self, "deleted", False)

            if old_deleted == current_deleted and not current_deleted:
                self.updated_at = timezone.now()

            if user:
                self.updated_by = user

        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        """
        Soft delete the record by setting deleted=True, deleted_at, and deleted_by.
        This ensures audit trail is maintained.
        """
        self.deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        models.Model.save(self, update_fields=["deleted", "deleted_at", "deleted_by"])

        return (1, {self.__class__.__name__: [self.pk]})


"""
NOTE:
API/view concerns like ArchiveMixin should not live in models modules.
See `common/api/mixins.py`.
"""
