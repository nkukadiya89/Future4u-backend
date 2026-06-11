from django.urls import path


class AuditSaveModelMixin:
    def save_model(self, request, obj, form, change):
        obj.save(user=request.user)


class ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RelatedDataAdminMixin:
    select_related_fields = ()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if self.select_related_fields:
            return qs.select_related(*self.select_related_fields)
        return qs


class ProfileReadonlyFieldsAdminMixin:
    profile_readonly_fields = ("user", "created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.profile_readonly_fields
        return ()


class MasterImportAdminURLMixin:
    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path(
                "upload/",
                self.admin_site.admin_view(self.upload_view),
                name="%s_%s_upload" % info,
            ),
            path(
                "sample-csv/",
                self.admin_site.admin_view(self.sample_csv_view),
                name="%s_%s_sample_csv" % info,
            ),
        ] + super().get_urls()
