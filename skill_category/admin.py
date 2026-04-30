from django.contrib import admin
from skill_category.models import SkillCategory, AssessmentInterestValue, AssessmentGoal


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'category_image_url', 'deleted', 'created_at')
    list_filter = ('deleted',)
    search_fields = ('category_name',)
    ordering = ('category_name',)
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(AssessmentInterestValue)
class AssessmentInterestValueAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'category_image_url', 'deleted', 'created_at')
    list_filter = ('deleted',)
    search_fields = ('category_name',)
    ordering = ('category_name',)
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')


@admin.register(AssessmentGoal)
class AssessmentGoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_url', 'deleted', 'created_at')
    list_filter = ('deleted',)
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at', 'deleted_at', 'deleted_by')

