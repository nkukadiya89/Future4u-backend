from django.contrib import admin

from token_override.models import TokenOverride


@admin.register(TokenOverride)
class TokenOverrideAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user",
        "entity_type",
        "entity_user_id",
        "extra_monthly_tokens",
        "valid_until",
        "is_active",
    ]
    list_filter = ["entity_type", "is_active"]
    search_fields = ["user__email", "user__full_name", "entity_type"]
