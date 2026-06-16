from django import forms
from django.contrib import admin

from common.mixins.admin_mixins import ProfileReadonlyFieldsAdminMixin
from user_profile.models import (
    BusinessSetting,
    ChildProfile,
    ParentProfile,
    ProfessionalProfile,
    StudentProfile,
    UserProfile,
)

admin.site.register(BusinessSetting)


class MultiSelectWidget(forms.CheckboxSelectMultiple):
    """Renders a JSONField as a multi-select checkbox list."""

    def format_value(self, value):
        if isinstance(value, str):
            import json

            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                value = []
        return super().format_value(value or [])


class MultiSelectField(forms.MultipleChoiceField):
    widget = MultiSelectWidget

    def to_python(self, value):
        return list(super().to_python(value)) if value else []

    def prepare_value(self, value):
        if isinstance(value, str):
            import json

            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return []
        return value or []


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = "__all__"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Base profile admin for Super Admin with language preference"""

    form = UserProfileAdminForm
    list_display = (
        "user",
        "get_language",
        "get_role",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("user", "get_role")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "get_role")
        return ("get_role",)

    @admin.display(description="Role")
    def get_role(self, obj):
        return obj.user.user_type if obj.user else "-"

    filter_horizontal = ("language",)
    list_select_related = ("user",)

    fieldsets = (
        ("Identity", {"fields": ("user", "get_role")}),
        ("Language", {"fields": ("language",)}),
    )

    @admin.display(description="Languages")
    def get_language(self, obj):
        return ", ".join(obj.language.values_list("name", flat=True)) or "-"


@admin.register(StudentProfile)
class StudentProfileAdmin(ProfileReadonlyFieldsAdminMixin, admin.ModelAdmin):
    """Student-specific profile admin with language and educational fields"""

    list_display = (
        "user",
        "science_track",
        "medium",
        "education_level",
        "stream",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("science_track", "medium")
    readonly_fields = ("user", "created_at", "updated_at")
    raw_id_fields = ("user", "education_level", "stream")

    autocomplete_fields = ("education_level", "stream")
    filter_horizontal = ("language",)
    list_select_related = (
        "user",
        "education_level",
        "stream",
    )

    fieldsets = (
        ("Identity", {"fields": ("user",)}),
        ("Language", {"fields": ("language",)}),
        (
            "Education",
            {"fields": ("education_level", "stream", "science_track", "medium")},
        ),
        (
            "Career Direction",
            {"fields": ("career_direction",)},
        ),
        (
            "Education Details",
            {"fields": ("education",)},
        ),
        (
            "Skills",
            {"fields": ("skills",)},
        ),
        (
            "Projects",
            {"fields": ("projects",)},
        ),
        (
            "Internships",
            {"fields": ("internships",)},
        ),
        (
            "Certifications",
            {"fields": ("certifications",)},
        ),
        (
            "Achievements",
            {"fields": ("achievements",)},
        ),
        (
            "Extra Activities",
            {"fields": ("extra_activities",)},
        ),
        (
            "Additional Insights",
            {"fields": ("additional_insights",)},
        ),
        (
            "Social Links",
            {"fields": ("linkedin_url", "github_url", "portfolio")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ParentProfile)
class ParentProfileAdmin(ProfileReadonlyFieldsAdminMixin, admin.ModelAdmin):
    """Parent-specific profile admin"""

    list_display = (
        "user",
        "relationship",
        "other_relationship_text",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = ("relationship",)
    readonly_fields = ("user", "created_at", "updated_at")
    raw_id_fields = ("user",)
    filter_horizontal = ("language",)
    list_select_related = ("user",)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "created_at", "updated_at")
        return ()

    fieldsets = (
        ("Identity", {"fields": ("user",)}),
        ("Language", {"fields": ("language",)}),
        ("About", {"fields": ("relationship", "other_relationship_text")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "parent_profile",
        "first_name",
        "last_name",
        "date_of_birth",
        "education_level",
        "stream",
        "academic_performance",
        "current_screen",
        "is_completed",
    )
    search_fields = (
        "first_name",
        "last_name",
        "parent_profile__user__email",
    )
    list_filter = (
        "is_completed",
        "current_screen",
        "education_level",
        "stream",
        "academic_performance",
        "deleted",
    )
    raw_id_fields = ("parent_profile", "education_level", "stream")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Parent", {"fields": ("parent_profile",)}),
        ("Child", {"fields": ("first_name", "last_name", "profile_image", "date_of_birth")}),
        ("Education", {"fields": ("education_level", "stream", "academic_performance")}),
        ("Flow", {"fields": ("current_screen", "is_completed")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(ProfileReadonlyFieldsAdminMixin, admin.ModelAdmin):
    """Professional-specific profile admin"""

    list_display = (
        "user",
        "employment_type",
        "years_of_experience",
        "education_level",
        "current_job_title",
    )
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "current_job_title",
    )
    list_filter = ("employment_type", "years_of_experience")
    readonly_fields = ("user", "created_at", "updated_at")
    raw_id_fields = ("user", "education_level")

    autocomplete_fields = ("education_level",)
    filter_horizontal = ("language",)
    list_select_related = (
        "user",
        "education_level",
    )

    fieldsets = (
        ("Identity", {"fields": ("user",)}),
        ("Language", {"fields": ("language",)}),
        (
            "Employment",
            {
                "fields": (
                    "employment_type",
                    "years_of_experience",
                    "current_job_title",
                    "current_industry",
                    "company_size",
                )
            },
        ),
        (
            "Education",
            {"fields": ("education_level",)},
        ),
        (
            "Career Direction",
            {"fields": ("career_direction",)},
        ),
        (
            "Education Details",
            {"fields": ("education",)},
        ),
        (
            "Work Experience",
            {"fields": ("work_experience",)},
        ),
        (
            "Skills",
            {"fields": ("skills",)},
        ),
        (
            "Certifications",
            {"fields": ("certifications",)},
        ),
        (
            "Key Highlights (Power Section)",
            {"fields": ("key_highlights",)},
        ),
        (
            "Additional High-Impact Data",
            {"fields": ("additional_insights",)},
        ),
        (
            "Social Links",
            {"fields": ("linkedin_url", "github_url", "portfolio")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
