from django.contrib import admin

from assessment.models import Option, Question, UserResponse


class OptionInline(admin.TabularInline):
    model = Option
    extra = 1


class MappedDomainFilter(admin.SimpleListFilter):
    title = "Mapped domain"
    parameter_name = "mapped_domain"

    def lookups(self, request, model_admin):
        # Keep list stable and readable; show name with code.
        Domain = Question.mapped_domains.rel.model
        rows = (
            Domain.objects.filter(deleted=False, is_active=True)
            .only("id", "domain_code", "domain_name")
            .order_by("domain_name", "domain_code")
        )
        return [(str(d.pk), f"{d.domain_name} ({d.domain_code})") for d in rows]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(mapped_domains__id=value)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "dimension", "signal_strength", "is_active", "question_text", "mapped_domains_list")
    list_filter = ("dimension", "is_active", MappedDomainFilter)
    search_fields = ("question_text", "mapped_domains__domain_name", "mapped_domains__domain_code")
    filter_horizontal = ("mapped_domains",)
    inlines = [OptionInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("mapped_domains").distinct()

    @admin.display(description="Mapped domains")
    def mapped_domains_list(self, obj: Question) -> str:
        # Keep it compact for list view; show domain codes when available.
        parts = []
        for d in obj.mapped_domains.all():
            code = (getattr(d, "domain_code", "") or "").strip()
            name = (getattr(d, "domain_name", "") or "").strip()
            parts.append(code or name)
        return ", ".join([p for p in parts if p])


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
