from django.contrib import admin

from domain.models import Domain

from assessment.models import (
    CareerDirection,
    CareerValue,
    Concern,
    Option,
    ParentAssessment,
    ParentCareerExpectation,
    ParentConstraint,
    Question,
    StudentAssessment,
    UserGoal,
    UserResponse,
    GuidanceReason,
    WorkConstraint,
    ProfessionalAssessment,
)

admin.site.register(CareerDirection)
admin.site.register(CareerValue)
admin.site.register(Concern)
admin.site.register(UserGoal)
admin.site.register(ParentCareerExpectation)
admin.site.register(ParentConstraint)
admin.site.register(GuidanceReason)
admin.site.register(WorkConstraint)


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
    )

    search_fields = (
        "user__email",
        "question__question_text",
    )

    list_filter = ("question__dimension",)


@admin.register(ParentAssessment)
class ParentAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "child",
        "domain_category",
        "domain",
        "parent_support",
        "career_familiarity",
        "decision_style",
        "current_screen",
        "is_completed",
        "created_at",
    )

    search_fields = (
        "user__email",
        "child__first_name",
        "child__last_name",
        "domain_category__domain_name",
        "domain_category__domain_code",
        "domain__domain_name",
        "domain__domain_code",
    )

    list_filter = (
        "is_completed",
        "current_screen",
        "domain_category",
        "domain",
        "parent_support",
        "career_familiarity",
        "decision_style",
    )

    fields = (
        "user",
        "child",
        "domain_category",
        "domain",
        "career_direction",
        "parent_support",
        "concerns",
        "parent_career_expectations",
        "limitations",
        "career_familiarity",
        "decision_style",
        "career_values",
        "user_goals",
        "current_screen",
        "is_completed",
    )

    filter_horizontal = (
        "career_direction",
        "concerns",
        "parent_career_expectations",
        "limitations",
        "career_values",
        "user_goals",
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain_category":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=True, deleted=False
            )
        if db_field.name == "domain":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=False, deleted=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain_category":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=True, deleted=False
            )
        if db_field.name == "domain":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=False, deleted=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ProfessionalAssessment)
class ProfessionalAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "career_intention",
        "preferred_environment",
        "preferred_structure",
        "domain_category",
        "domain",
        "salary_expectation",
        "timeline",
        "current_screen",
        "is_completed",
        "created_at",
    )

    list_filter = (
        "is_completed",
        "current_screen",
        "career_intention",
        "preferred_environment",
        "preferred_structure",
    )

    search_fields = (
        "user__email",
        "domain_category__domain_name",
        "domain_category__domain_code",
        "domain__domain_name",
        "domain__domain_code",
    )

    raw_id_fields = ("domain_category", "domain")

    filter_horizontal = (
        "guidance_reasons",
        "work_constraints",
        "career_values",
        "platform_goals",
    )

    list_select_related = ("domain_category", "domain")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "domain_category":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=True, deleted=False
            )
        if db_field.name == "domain":
            kwargs["queryset"] = Domain.objects.filter(
                parent__isnull=False, deleted=False
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
