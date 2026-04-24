from rest_framework.routers import DefaultRouter

from skill_category.views import SkillCategoryViewSet

skill_category_router = DefaultRouter()
skill_category_router.register("skill-categories", SkillCategoryViewSet, basename="skill-category")
