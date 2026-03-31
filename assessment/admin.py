from django.contrib import admin

from assessment.models import Option, Question, UserResponse


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "dimension", "signal_strength", "is_active", "question_text")
    list_filter = ("dimension", "is_active")
    search_fields = ("question_text",)
    filter_horizontal = ("mapped_domains",)
    inlines = [OptionInline]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "option_text", "score_value")
    search_fields = ("option_text", "question__question_text")
    list_filter = ("score_value", "question__dimension")


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "question", "selected_option", "score_value")
    search_fields = ("user__email", "question__question_text")
    list_filter = ("question__dimension", "score_value")
