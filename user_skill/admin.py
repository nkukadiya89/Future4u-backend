from django.contrib import admin

from user_skill.models import UserSkill


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "proficiency_score")
    list_filter = ("skill",)
    search_fields = ("user__email", "user__first_name", "user__last_name")
