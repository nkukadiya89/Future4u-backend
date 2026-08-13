import django_filters
from django.db.models import F

from user_profile.models import ParentProfile, Profile


PROFILE_USER_ANNOTATIONS = {
    "country": F("user__country__name"),
    "state": F("user__states__name"),
    "city": F("user__city__name"),
    "address": F("user__address"),
    "first_name": F("user__first_name"),
    "last_name": F("user__last_name"),
    "phone": F("user__phone"),
    "email": F("user__email"),
    "status": F("user__status"),
    "user_type": F("user__user_type"),
}


def apply_user_location_filters(queryset, query_params):
    status_filter = query_params.get("status")
    city_id = query_params.get("city")
    state_id = query_params.get("state")
    country_id = query_params.get("country")

    if status_filter:
        queryset = queryset.filter(user__status=status_filter)
    if city_id:
        queryset = queryset.filter(user__city_id=city_id)
    if state_id:
        queryset = queryset.filter(user__states_id=state_id)
    if country_id:
        queryset = queryset.filter(user__country_id=country_id)
    return queryset


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
