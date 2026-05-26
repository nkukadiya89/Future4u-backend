from django.contrib import admin

from .models import CareerRecommendation, CareerRecommendationSuggestion


class CareerRecommendationSuggestionInline(admin.TabularInline):
    model = CareerRecommendationSuggestion
    extra = 0
    fields = (
        "display_order",
        "career_name",
        "match_percentage",
        "ai_insight",
    )
    ordering = ("display_order", "id")
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted=False)


@admin.register(CareerRecommendation)
class CareerRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "assessment",
        "last_recommended_at",
        "suggestion_count",
        "deleted",
        "created_at",
    )
    list_filter = (
        "deleted",
        "last_recommended_at",
        "created_at",
    )
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "assessment__id",
        "suggestions__career_name",
    )
    raw_id_fields = ("user", "assessment")
    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "deleted_at",
        "deleted_by",
    )
    inlines = [CareerRecommendationSuggestionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "assessment")
            .prefetch_related("suggestions")
        )

    @admin.display(description="Suggestions")
    def suggestion_count(self, obj):
        return obj.suggestions.filter(deleted=False).count()


@admin.register(CareerRecommendationSuggestion)
class CareerRecommendationSuggestionAdmin(admin.ModelAdmin):
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
        "recommendation__assessment__id",
    )
    raw_id_fields = ("recommendation",)
    ordering = ("recommendation", "display_order", "id")
