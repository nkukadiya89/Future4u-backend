from django.conf import settings
from django.db import models
from django.utils.timezone import now
from django.contrib.postgres.fields import ArrayField
from city.models import City
from company.models import Company
from country.models import Country
from state.models import State


class UserProfile(models.Model):
    """Base profile for Super Admin with language preference"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    language = models.ManyToManyField(
        "language_master.Language",
        blank=True,
        related_name="user_profiles",
        help_text="Preferred languages selected from Language master",
    )

    def __str__(self):
        return f"Profile<{self.user_id}>"

    class Meta:
        db_table = "user_profile"


class StudentProfile(models.Model):
    """Student-specific profile with common and educational details"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    # Common fields
    language = models.ManyToManyField(
        "language_master.Language",
        blank=True,
        related_name="student_profiles",
        help_text="Preferred languages selected from Language master",
    )

    # Student-specific fields
    class ScienceTrack(models.TextChoices):
        PCM = "pcm", "PCM (Physics, Chemistry, Maths)"
        PCB = "pcb", "PCB (Physics, Chemistry, Biology)"
        PCMB = "pcmb", "PCMB (All four)"

    science_track = models.CharField(
        max_length=10,
        choices=ScienceTrack.choices,
        null=True,
        blank=True,
        help_text="Science track selection for students",
    )

    medium = models.CharField(
        max_length=20,
        choices=[
            ("english", "English"),
            ("hindi", "Hindi"),
            ("gujarati", "Gujarati"),
        ],
        null=True,
        blank=True,
        help_text="Instruction medium of student's school",
    )

    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
    )

    stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"StudentProfile<{self.user_id}>"

    class Meta:
        db_table = "student_profile"


class BusinessSetting(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_business_setting",
        null=True,
    )

    user_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="user_business_settings",
        help_text="User who created this business setting",
    )

    notifications = models.BooleanField(default=True)
    sgst = models.FloatField(default=0, null=True, blank=True)
    cgst = models.FloatField(default=0, null=True, blank=True)
    igst = models.FloatField(default=0, null=True, blank=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_country",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_state",
    )
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_settings_city",
    )
    currency = models.CharField(max_length=5, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_setting_created",
    )
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_setting_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_setting_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.company}"

    class Meta:
        db_table = "business_setting"


class Profile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profiles"
    )

    title = models.CharField(max_length=150)  

    country = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)

    completion_percentage = models.IntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profile_created",
    )
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profile_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile<{self.id} - {self.title}>"

    class Meta:
        db_table = "profile"
        ordering = ["-created_at"]


class ProfessionalProfile(models.Model):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="professional"
    )

    # About
    employment_type = models.CharField(
        max_length=50
    )  # salaried / self-employed / freelancer / job seeker

    # Current Role
    current_job_title = models.CharField(max_length=150, null=True, blank=True)
    current_industry = models.CharField(max_length=100, null=True, blank=True)
    company_size = models.CharField(max_length=50, null=True, blank=True)

    # Experience & Education
    years_of_experience = models.IntegerField(null=True, blank=True)
    highest_education = models.CharField(max_length=150, null=True, blank=True)

    # Career Goals
    career_goal = models.CharField(max_length=100)  # promotion / switch / startup etc.

    # Constraints (multi-select → separate table better)
    # storing as JSON for speed initially
    constraints = models.JSONField(default=list, blank=True)

    # Work Preferences
    work_mode = models.CharField(
        max_length=50, null=True, blank=True
    )  # remote/hybrid/office
    work_structure = models.CharField(
        max_length=50, null=True, blank=True
    )  # fixed/flexible

    # Industries
    preferred_industries = models.JSONField(default=list, blank=True)

    # Values
    career_values = models.JSONField(default=list, blank=True)

    # Salary
    expected_salary_range = models.CharField(max_length=50, null=True, blank=True)

    # Timeline
    transition_timeline = models.CharField(max_length=50, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="professional_profile_created",
    )
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="professional_profile_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professional_profile_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ProfessionalProfile<{self.id} - {self.profile.title}>"

    class Meta:
        db_table = "professional_profile"
        ordering = ["-created_at"]


class ParentProfile(models.Model):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="parent"
    )

    relation = models.CharField(max_length=50)  # mother/father/guardian

    # Child Info
    child_name = models.CharField(max_length=150)
    child_education_level = models.CharField(max_length=100)
    stream = models.CharField(max_length=100, null=True, blank=True)
    academic_performance = models.CharField(max_length=50, null=True, blank=True)

    # Interests
    child_interests = models.JSONField(default=list, blank=True)

    # Parent behavior
    support_level = models.CharField(max_length=50)

    # Child future plan
    child_goal = models.CharField(max_length=100)

    # Parent expectations
    parent_expectations = models.JSONField(default=list, blank=True)

    # Concerns
    concerns = models.JSONField(default=list, blank=True)

    # Constraints
    constraints = models.JSONField(default=list, blank=True)

    # Awareness
    career_awareness = models.CharField(max_length=50)

    # Decision style
    decision_style = models.CharField(max_length=50)

    # Values
    values = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="parent_profile_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profile_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ParentProfile<{self.id} - {self.profile.title}>"

    class Meta:
        db_table = "parent_profile"
        ordering = ["-created_at"]


class CorporateProfile(models.Model):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="corporate"
    )

    # Organization Type
    organization_type = models.CharField(max_length=100)  # HR / CEO / etc.

    # Company Info
    company_name = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    company_size = models.CharField(max_length=50)

    # Hiring Intent
    hiring_purpose = models.JSONField(default=list, blank=True)

    # Hiring Requirements
    roles_hiring_for = models.JSONField(default=list, blank=True)
    experience_level = models.CharField(max_length=50)

    # Skills needed
    required_skills = models.JSONField(default=list, blank=True)

    # Training needs
    training_needs = models.JSONField(default=list, blank=True)

    # Target candidates
    target_candidates = models.JSONField(default=list, blank=True)

    # Engagement model
    engagement_model = models.JSONField(default=list, blank=True)

    # Timeline & Budget
    hiring_timeline = models.CharField(max_length=50)
    budget_range = models.CharField(max_length=50)

    # Company values
    company_values = models.JSONField(default=list, blank=True)

    # Challenges
    challenges = models.JSONField(default=list, blank=True)

    # Goals
    goals = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="corporate_profile_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="corporate_profile_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CorporateProfile<{self.id} - {self.profile.title}>"

    class Meta:
        db_table = "corporate_profile"
        ordering = ["-created_at"]
