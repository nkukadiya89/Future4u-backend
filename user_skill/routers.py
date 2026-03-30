from rest_framework.routers import DefaultRouter

from user_skill.views import UserSkillViewSet

user_skill_router = DefaultRouter()
user_skill_router.register("user-skills", UserSkillViewSet, basename="user_skills")
