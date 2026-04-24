from django.urls import path, include
from rest_framework.routers import DefaultRouter
from skill_category.views import SkillCategoryViewSet

router = DefaultRouter()
router.register(r"", SkillCategoryViewSet, basename="skill-category")

urlpatterns = [
    path("skill-categories/", include(router.urls)),
]
