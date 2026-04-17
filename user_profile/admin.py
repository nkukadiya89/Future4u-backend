from django import forms
from django.contrib import admin

from user_profile.models import BusinessSetting, UserProfile

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
    career_goal = MultiSelectField(
        choices=UserProfile.CareerGoal.choices, required=False
    )
    interest_categories = MultiSelectField(
        choices=UserProfile.InterestCategory.choices, required=False
    )
    user_concerns = MultiSelectField(
        choices=UserProfile.UserConcern.choices, required=False
    )
    career_values = MultiSelectField(
        choices=UserProfile.CareerValue.choices, required=False
    )
    platform_goals = MultiSelectField(
        choices=UserProfile.PlatformGoal.choices, required=False
    )

    class Meta:
        model = UserProfile
        fields = "__all__"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = (
        "user",
        "education_level",
        "stream",
        "science_track",
        "medium",
        "country",
        "state",
        "city",
        "get_career_goal",
        "parent_support_level",
        "get_language",
        "get_interest_categories",
        "get_user_concerns",
        "get_career_values",
        "get_platform_goals",
    )
    search_fields = ("user__email", "user__first_name", "user__last_name")
    list_filter = (
        "science_track",
        "parent_support_level",
        "medium",
    )
    readonly_fields = ("user", "get_role")
    raw_id_fields = ("user", "country", "state", "city")

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("user", "get_role")
        return ("get_role",)

    @admin.display(description="Role")
    def get_role(self, obj):
        return obj.user.user_type if obj.user else "-"

    autocomplete_fields = ("education_level", "stream")
    filter_horizontal = ("language",)
    list_select_related = (
        "user",
        "education_level",
        "stream",
        "country",
        "state",
        "city",
    )

    fieldsets = (
        ("Identity", {"fields": ("user", "get_role")}),
        (
            "Education",
            {"fields": ("education_level", "stream", "science_track", "medium")},
        ),
        ("Location & Language", {"fields": ("language", "country", "state", "city")}),
        (
            "Onboarding",
            {
                "fields": (
                    "interest_categories",
                    "career_goal",
                    "parent_support_level",
                    "user_concerns",
                    "career_values",
                    "platform_goals",
                )
            },
        ),
    )

    @admin.display(description="Languages")
    def get_language(self, obj):
        return ", ".join(obj.language.values_list("name", flat=True)) or "-"

    @admin.display(description="Career Goal")
    def get_career_goal(self, obj):
        return ", ".join(obj.career_goal) if obj.career_goal else "-"

    @admin.display(description="Interests")
    def get_interest_categories(self, obj):
        return ", ".join(obj.interest_categories) if obj.interest_categories else "-"

    @admin.display(description="Concerns")
    def get_user_concerns(self, obj):
        return ", ".join(obj.user_concerns) if obj.user_concerns else "-"

    @admin.display(description="Career Values")
    def get_career_values(self, obj):
        return ", ".join(obj.career_values) if obj.career_values else "-"

    @admin.display(description="Platform Goals")
    def get_platform_goals(self, obj):
        return ", ".join(obj.platform_goals) if obj.platform_goals else "-"
