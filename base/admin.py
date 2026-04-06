from django.contrib import admin


class BaseAdminMixin:
    list_filter = ("is_active", "deleted")
    actions = (
        "activate_selected",
        "deactivate_selected",
        "archive_selected",
        "restore_selected",
    )

    def _bulk_set_active(self, request, queryset, is_active: bool):
        return queryset.update(is_active=is_active)

    def _archive_object(self, request, obj):
        if hasattr(obj, "soft_delete"):
            obj.soft_delete(user=request.user)
        else:
            obj.deleted = True
            obj.save(user=request.user)

    def _restore_object(self, request, obj):
        obj.deleted = False
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = None
        if hasattr(obj, "deleted_by"):
            obj.deleted_by = None
        obj.save(user=request.user)

    @admin.action(description="Activate selected")
    def activate_selected(self, request, queryset):
        count = self._bulk_set_active(request, queryset, True)
        self.message_user(request, f"{count} record(s) activated.")

    @admin.action(description="Deactivate selected")
    def deactivate_selected(self, request, queryset):
        count = self._bulk_set_active(request, queryset, False)
        self.message_user(request, f"{count} record(s) deactivated.")

    @admin.action(description="Archive selected (soft)")
    def archive_selected(self, request, queryset):
        count = 0
        for obj in queryset.filter(deleted=False):
            self._archive_object(request, obj)
            count += 1
        self.message_user(request, f"{count} record(s) archived.")

    @admin.action(description="Restore selected")
    def restore_selected(self, request, queryset):
        count = 0
        for obj in queryset.filter(deleted=True):
            self._restore_object(request, obj)
            count += 1
        self.message_user(request, f"{count} record(s) restored.")


class BaseAdmin(BaseAdminMixin, admin.ModelAdmin):
    """
    Reusable admin actions for active/archive status.
    Child admins can override hook methods for custom behavior.
    """

    search_fields = ()
