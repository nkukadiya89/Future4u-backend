from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from user.models import CustomGroup, EmailPhoneVerify, RoleFamily, User

# Register your models here.


class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "user_type", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "user_type", "status")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-id",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name", "full_name", "phone", "profile_image", "about_me", "designation")}),
        (
            "Location",
            {"fields": ("country", "states", "city")},
        ),
        (
            "Additional info",
            {
                "fields": (
                    "user_type",
                    "status",
                    "email_verified",
                    "otp",
                    "keep_me_logged_in",
                    "terms_accepted",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "password_last_changed")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "username",
                    "first_name",
                    "last_name",
                    "full_name",
                    "phone",
                    "profile_image",
                    "about_me",
                    "designation",
                    "country",
                    "states",
                    "city",
                    "user_type",
                    "status",
                    "email_verified",
                    "otp",
                    "keep_me_logged_in",
                    "terms_accepted",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "last_login",
                    "date_joined",
                    "password_last_changed",
                ),
            },
        ),
    )

    def response_add(self, request, obj, post_url_continue=None):
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        return HttpResponseRedirect(reverse("admin:user_user_changelist"))


admin.site.register(User, UserAdmin)
admin.site.register(RoleFamily)
admin.site.register(EmailPhoneVerify)


class CustomGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sequence")


admin.site.register(CustomGroup, CustomGroupAdmin)
