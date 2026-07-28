import django_filters

from user_profile.models import ParentProfile, Profile


class ProfileFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    city = django_filters.CharFilter(lookup_expr="icontains")
    country = django_filters.CharFilter(lookup_expr="icontains")
    user = django_filters.NumberFilter(field_name="user_id")

    class Meta:
        model = Profile
        fields = ["title", "city", "country", "user"]


class ParentProfileFilter(django_filters.FilterSet):
    relationship = django_filters.CharFilter(lookup_expr="icontains")
    other_relationship_text = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = ParentProfile
        fields = [
            "relationship",
            "other_relationship_text",
        ]
