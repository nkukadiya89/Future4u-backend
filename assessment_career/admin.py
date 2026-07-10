from django.contrib import admin

from common.mixins.admin_mixins import ReadOnlyAdminMixin
from .models import (
    CareerRecommendation,
    CareerSuggestion,
    ChatMessage,
    ChatSession,
)


class CareerSuggestionInline(admin.TabularInline):
    model = CareerSuggestion
    extra = 0
    fields = (
        "id",
        "display_order",
        "career_name",
        "match_percentage",
    )
    readonly_fields = ("id",)
    ordering = ("display_order", "id")
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted=False)


class ChatMessageInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = ChatMessage
    extra = 0
    fields = ("id", "role", "content", "created_at")
    readonly_fields = ("id", "role", "content", "created_at")
    ordering = ("created_at", "id")


@admin.register(CareerRecommendation)
class CareerRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile_type",
        "user",
        "assessment_link",
        "last_recommended_at",
        "suggestion_count",
        "deleted",
        "created_at",
    )
    list_filter = (
        "profile_type",
        "deleted",
        "last_recommended_at",
        "created_at",
    )
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "suggestions__career_name",
    )
    raw_id_fields = ("user", "student_assessment", "parent_assessment")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
        "raw_ai_response",
        "easy_decision_making",
        "last_recommended_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "profile_type",
                    "user",
                    "student_assessment",
                    "parent_assessment",
                    "last_recommended_at",
                    "deleted",
                )
            },
        ),
        (
            "AI payload",
            {
                "classes": ("collapse",),
                "fields": ("easy_decision_making", "raw_ai_response"),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
            },
        ),
    )
    inlines = [CareerSuggestionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "student_assessment", "parent_assessment")
            .prefetch_related("suggestions")
        )

    @admin.display(description="Assessment")
    def assessment_link(self, obj):
        return obj.student_assessment_id or obj.parent_assessment_id

    @admin.display(description="Suggestions")
    def suggestion_count(self, obj):
        return obj.suggestions.filter(deleted=False).count()


# CareerSuggestion


@admin.register(CareerSuggestion)
class CareerSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recommendation",
        "career_name",
        "match_percentage",
        "display_order",
        "deleted",
        "created_at",
    )
    list_filter = (
        "deleted",
        "display_order",
        "created_at",
    )
    search_fields = (
        "career_name",
        "ai_insight",
        "recommendation__user__email",
    )
    raw_id_fields = ("recommendation",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "recommendation",
                    "career_name",
                    "match_percentage",
                    "display_order",
                    "ai_insight",
                    "deleted",
                )
            },
        ),
        (
            "Structured data",
            {
                "classes": ("collapse",),
                "fields": (
                    "why_this_career",
                    "required_skills",
                    "required_education",
                    "career_factors",
                    "career_roadmap",
                ),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
            },
        ),
    )
    ordering = ("recommendation", "display_order", "id")


# ChatSession


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "suggestion",
        "child_link",
        "message_count",
        "updated_at",
        "created_at",
    )
    list_select_related = ("child", "suggestion")
    search_fields = (
        "suggestion__career_name",
        "suggestion__recommendation__user__email",
        "child__first_name",
        "child__last_name",
    )
    raw_id_fields = ("suggestion", "child")
    readonly_fields = ("summary", "created_at", "updated_at")
    inlines = [ChatMessageInline]

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.messages.filter(deleted=False).count()

    @admin.display(description="Child")
    def child_link(self, obj):
        if obj.child_id:
            return str(obj.child) if obj.child else f"ID {obj.child_id}"
        return "-"
