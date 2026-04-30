from common.api.mixins import ArchiveMixin
from common.master_view import BaseModelViewSet
from rest_framework.permissions import DjangoModelPermissions

from assessment.models import AssessmentInterestCategory
from assessment.serializers import AssessmentInterestCategorySerializer


class AssessmentInterestCategoryViewSet(BaseModelViewSet, ArchiveMixin):
    queryset = AssessmentInterestCategory.objects.all().order_by(
        "sequence_order",
        "category_name",
    )
    serializer_class = AssessmentInterestCategorySerializer
    permission_classes = [DjangoModelPermissions]

    search_fields = BaseModelViewSet.searching_fields + [
        "category_code",
        "category_name",
    ]
    ordering_fields = BaseModelViewSet.ordering_fields + [
        "sequence_order",
        "category_name",
    ]
