from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm
from django.utils import timezone

from user.models import CustomGroup, EmailPhoneVerify, RoleFamily, User
from user.services.registration_service import setup_web_user_password


class UserChangeForm(BaseUserChangeForm):
    username = forms.CharField(required=False, max_length=60)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and not self.instance.username:
            self.instance.username = ""

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username:
            return self.instance.email if self.instance.email else ""
        return username

    def clean_password(self):
        return self.initial.get("password") or ""


class UserAdminAddForm(forms.ModelForm):
    """Add user in admin — no password fields; temp password is emailed after save."""

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "profile_image",
            "about_me",
            "designation",
            "country",
            "states",
            "city",
            "address",
            "user_type",
            "terms_accepted",
            "referral_code",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
        help_texts = {
            "email": (
                "A password setup link will be sent to this email. "
                "The user must set their password before logging in."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["last_name"].required = True
        self.fields["terms_accepted"].initial = True
        self.fields["terms_accepted"].required = True
        self.fields["email"].required = True
        self.fields["phone"].required = True
        self.fields["country"].required = True
        self.fields["states"].required = True
        self.fields["city"].required = True

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if not username:
            return self.cleaned_data.get("email") or ""
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if not user.username:
            user.username = user.email or ""
        user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserAdminAddForm
    list_display = (
        "email",
        "first_name",
        "last_name",
        "user_type",
        "is_org_staff",
        "created_by",
        "is_active",
        "is_staff",
        "must_change_password",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "user_type",
        "is_org_staff",
        "status",
        "must_change_password",
        "deleted",
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-id",)
    readonly_fields = (
        "created_by",
        "created_at",
        "updated_by",
        "updated_at",
        "deleted",
        "deleted_at",
        "deleted_by",
        "is_org_staff",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "full_name",
                    "phone",
                    "profile_image",
                    "about_me",
                    "designation",
                )
            },
        ),
        (
            "Location",
            {"fields": ("country", "states", "city", "address")},
        ),
        (
            "Additional info",
            {
                "fields": (
                    "user_type",
                    "is_org_staff",
                    "status",
                    "email_verified",
                    "must_change_password",
                    "otp",
                    "keep_me_logged_in",
                    "terms_accepted",
                    "referral_code",
                    "created_by",
                    "created_at",
                    "updated_by",
                    "updated_at",
                    "deleted",
                    "deleted_at",
                    "deleted_by",
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
        (
            "Important dates",
            {"fields": ("last_login", "date_joined", "password_last_changed")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "description": (
                    "No password is required. After you save, a password setup link "
                    "will be emailed to the user. They must set their password before logging in."
                ),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "phone",
                    "user_type",
                    "country",
                    "states",
                    "city",
                    "terms_accepted",
                    "referral_code",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                    "status",
                    "email_verified",
                ),
            },
        ),
        (
            "Optional details",
            {
                "classes": ("wide",),
                "fields": (
                    "profile_image",
                    "about_me",
                    "designation",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        else:
            obj.updated_by = request.user
            obj.updated_at = timezone.now()
        super().save_model(request, obj, form, change)
        if not change:
            setup_web_user_password(obj)
            self.message_user(
                request,
                f"User created successfully. A password setup link has been sent to {obj.email}.",
                messages.SUCCESS,
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
