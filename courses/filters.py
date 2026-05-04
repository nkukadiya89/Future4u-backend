import django_filters

from .models import Course, CourseEnrollment


class CourseFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    level = django_filters.CharFilter()
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    domain = django_filters.NumberFilter(field_name="domains__id")
    skill = django_filters.NumberFilter(field_name="skills__id")

    class Meta:
        model = Course
        fields = ["level", "domain", "skill"]


class CourseEnrollmentFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    course = django_filters.NumberFilter(field_name="course_id")

    class Meta:
        model = CourseEnrollment
        fields = ["status", "course"]