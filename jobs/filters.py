import django_filters

from jobs.models import Job, JobApplication, JobPreference, JobSkill, SavedJob


class JobFilters(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr="icontains")
    company_name = django_filters.CharFilter(lookup_expr="icontains")
    domain = django_filters.NumberFilter(field_name="domain_id")
    employment_type = django_filters.CharFilter(lookup_expr="iexact")
    experience_min = django_filters.NumberFilter(
        field_name="experience_min", lookup_expr="gte"
    )
    experience_max = django_filters.NumberFilter(
        field_name="experience_max", lookup_expr="lte"
    )
    salary_min = django_filters.NumberFilter(field_name="salary_min", lookup_expr="gte")
    salary_max = django_filters.NumberFilter(field_name="salary_max", lookup_expr="lte")
    location = django_filters.CharFilter(lookup_expr="icontains")
    work_mode = django_filters.CharFilter(lookup_expr="iexact")

    # Add filters for new fields
    job_type = django_filters.CharFilter(lookup_expr="iexact")
    application_deadline = django_filters.DateTimeFilter(
        field_name="application_deadline", lookup_expr="exact"
    )
    application_deadline_before = django_filters.DateTimeFilter(
        field_name="application_deadline", lookup_expr="lte"
    )
    application_deadline_after = django_filters.DateTimeFilter(
        field_name="application_deadline", lookup_expr="gte"
    )

    class Meta:
        model = Job
        fields = [
            "title",
            "company_name",
            "domain",
            "employment_type",
            "experience_min",
            "experience_max",
            "salary_min",
            "salary_max",
            "location",
            "work_mode",
            "job_type",
            "application_deadline",
            "application_deadline_before",
            "application_deadline_after",
        ]


class JobSkillFilter(django_filters.FilterSet):
    skill_name = django_filters.CharFilter(
        field_name="skill__name", lookup_expr="icontains"
    )
    job = django_filters.NumberFilter(field_name="job_id")

    class Meta:
        model = JobSkill
        fields = ["skill_name", "job"]


class JobPreferenceFilter(django_filters.FilterSet):
    preferred_industries = django_filters.CharFilter(lookup_expr="icontains")
    soft_skills = django_filters.CharFilter(
        field_name="soft_skills__name", lookup_expr="icontains"
    )
    education_requirement = django_filters.CharFilter(lookup_expr="icontains")
    notice_period_days = django_filters.NumberFilter(lookup_expr="lte")
    job = django_filters.NumberFilter(field_name="job_id")

    class Meta:
        model = JobPreference
        fields = [
            "preferred_industries",
            "soft_skills",
            "education_requirement",
            "notice_period_days",
            "job",
        ]


class JobApplicationFilter(django_filters.FilterSet):
    profile = django_filters.NumberFilter(field_name="profile_id")
    applicant = django_filters.NumberFilter(field_name="user_id")
    job = django_filters.NumberFilter(field_name="job_id")
    status = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = JobApplication
        fields = ["profile", "applicant", "job", "status"]


class SavedJobFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name="user_id")
    job = django_filters.NumberFilter(field_name="job_id")

    class Meta:
        model = SavedJob
        fields = ["user", "job"]
