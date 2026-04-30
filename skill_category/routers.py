from rest_framework.routers import DefaultRouter

from skill_category.views import (
    SkillCategoryViewSet,
    AssessmentInterestValueViewSet,
    AssessmentGoalViewSet,
)

skill_category_router = DefaultRouter()
skill_category_router.register("skill-categories", SkillCategoryViewSet, basename="skill-category")
skill_category_router.register(
    "assessment-interest-values",
    AssessmentInterestValueViewSet,
    basename="assessment-interest-value",
)
skill_category_router.register(
    "assessment-goals",
    AssessmentGoalViewSet,
    basename="assessment-goal",
)
