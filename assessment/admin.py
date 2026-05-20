from django.contrib import admin

from assessment.models import (
    Option,
    Question,
    StudentAssessment,
    UserResponse,
)


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class MappedDomainFilter(admin.SimpleListFilter):
    title = "Mapped domain"
    parameter_name = "mapped_domain"

    def lookups(self, request, model_admin):
        Domain = Question.mapped_domains.rel.model

        rows = (
            Domain.objects.filter(
                deleted=False,
                is_active=True,
            )
            .only("id", "domain_code", "domain_name")
            .order_by("domain_name", "domain_code")
        )

        return [
            (
                str(d.pk),
                f"{d.domain_name} ({d.domain_code})",
            )
            for d in rows
        ]

    def queryset(self, request, queryset):
        value = self.value()

        if not value:
            return queryset

        return queryset.filter(mapped_domains__id=value)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dimension",
        "signal_strength",
        "education_level",
        "target_stream",
        "is_active",
        "question_text",
        "mapped_domains_list",
        "mapped_streams_list",
    )

    list_filter = (
        "dimension",
        "education_level",
        "target_stream",
        "is_active",
        MappedDomainFilter,
    )

    search_fields = (
        "question_text",
        "mapped_domains__domain_name",
        "mapped_domains__domain_code",
        "mapped_streams__stream_name",
        "mapped_streams__stream_code",
    )

    filter_horizontal = (
        "mapped_domains",
        "mapped_streams",
    )

    raw_id_fields = (
        "education_level",
        "target_stream",
    )

    inlines = [OptionInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.prefetch_related(
            "mapped_domains",
            "mapped_streams",
        ).distinct()

    @admin.display(description="Mapped domains")
    def mapped_domains_list(self, obj):
        parts = []

        for d in obj.mapped_domains.all():
            code = (getattr(d, "domain_code", "") or "").strip()
            name = (getattr(d, "domain_name", "") or "").strip()

            parts.append(code or name)

        return ", ".join([p for p in parts if p])

    @admin.display(description="Mapped streams")
    def mapped_streams_list(self, obj):
        parts = []

        for stream in obj.mapped_streams.all():
            code = (getattr(stream, "stream_code", "") or "").strip()
            name = (getattr(stream, "stream_name", "") or "").strip()

            parts.append(code or name)

        return ", ".join([p for p in parts if p])


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "question",
        "option_text",
    )

    search_fields = (
        "option_text",
        "question__question_text",
    )

    list_filter = ("question__dimension",)


@admin.register(UserResponse)
class UserResponseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "question",
        "selected_option",
        "get_score",
    )

    search_fields = (
        "user__email",
        "question__question_text",
    )

    list_filter = ("question__dimension",)

    @admin.display(description="Score")
    def get_score(self, obj):
        if obj.selected_option:
            return getattr(obj.selected_option, "score_value", None)

        return None


@admin.register(StudentAssessment)
class StudentAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "domain_category",
        "domain",
        "parent_support",
        "current_screen",
        "is_completed",
        "created_at",
    )

    search_fields = (
        "user__email",
        "domain_category__domain_code",
        "domain_category__domain_name",
        "domain__domain_code",
        "domain__domain_name",
    )

    list_filter = (
        "is_completed",
        "current_screen",
        "domain_category",
        "domain",
    )
