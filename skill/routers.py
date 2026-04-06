from rest_framework.routers import DefaultRouter

from skill.views import SkillViewSet

skill_router = DefaultRouter()
skill_router.register("api/skills", SkillViewSet, basename="skill")
