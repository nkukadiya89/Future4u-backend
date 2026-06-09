import django_filters

from user_profile.models import (
    ParentProfile,
    Profile,
)


class ProfileFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    city = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="icontains")
    user = django_filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Profile
        fields = ["title", "city", "country", "user"]

class ParentProfileFilter(django_filters.FilterSet):
    relation = django_filters.CharFilter(lookup_expr="icontains")
    child_name = django_filters.CharFilter(lookup_expr="icontains")
    child_education_level = django_filters.CharFilter(lookup_expr="icontains")
    stream = django_filters.CharFilter(lookup_expr="icontains")
    academic_performance = django_filters.CharFilter(lookup_expr="icontains")
    support_level = django_filters.CharFilter(lookup_expr="icontains")
    child_goal = django_filters.CharFilter(lookup_expr="icontains")
    career_awareness = django_filters.CharFilter(lookup_expr="icontains")
    decision_style = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = ParentProfile
        fields = [
            "relation",
            "child_name",
            "child_education_level",
            "stream",
            "academic_performance",
            "support_level",
            "child_goal",
            "career_awareness",
            "decision_style",
        ]
