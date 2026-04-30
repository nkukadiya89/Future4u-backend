from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, DjangoModelPermissions
from rest_framework.response import Response
from common.master_view import BaseModelViewSet
from common.api.mixins import ArchiveMixin
from skill_category.models import SkillCategory, AssessmentInterestValue, AssessmentGoal
from skill_category.serializers import SkillCategorySerializer, AssessmentInterestValueSerializer, AssessmentGoalSerializer


class SkillCategoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = SkillCategory.objects.all().order_by("category_name")
    serializer_class = SkillCategorySerializer
    permission_classes = [DjangoModelPermissions]
    

    search_fields = BaseModelViewSet.searching_fields + [
        "category_name",
        "category_image_url",
    ]
    
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "category_name",
    ]


class AssessmentInterestValueViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AssessmentInterestValue.objects.all().order_by("category_name")
    serializer_class = AssessmentInterestValueSerializer
    permission_classes = [DjangoModelPermissions]

    search_fields = BaseModelViewSet.searching_fields + [
        "category_name",
        "category_image_url",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "category_name",
    ]


class AssessmentGoalViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AssessmentGoal.objects.all().order_by("name")
    serializer_class = AssessmentGoalSerializer
    permission_classes = [DjangoModelPermissions]

    search_fields = BaseModelViewSet.searching_fields + [
        "name",
        "image_url",
    ]

    ordering_fields = BaseModelViewSet.ordering_fields + [
        "name",
    ]

