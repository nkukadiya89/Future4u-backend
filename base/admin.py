from django.contrib import admin


class BaseAdmin(admin.ModelAdmin):
    """
    Reusable admin actions for active/archive status.
    Child admins can override hook methods for custom behavior.
    """

    list_filter = ("is_active", "is_archived")
    search_fields = ()

    actions = (
        "activate_selected",
        "deactivate_selected",
        "archive_selected",
        "restore_selected",
    )

    def _bulk_set_active(self, request, queryset, is_active: bool):
        return queryset.update(is_active=is_active)

    def _archive_object(self, request, obj):
        obj.is_archived = True
        obj.save(user=request.user)

    def _restore_object(self, request, obj):
        obj.is_archived = False
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
        for obj in queryset.filter(is_archived=False):
            self._archive_object(request, obj)
            count += 1
        self.message_user(request, f"{count} record(s) archived.")

    @admin.action(description="Restore selected")
    def restore_selected(self, request, queryset):
        count = 0
        for obj in queryset.filter(is_archived=True):
            self._restore_object(request, obj)
            count += 1
        self.message_user(request, f"{count} record(s) restored.")

