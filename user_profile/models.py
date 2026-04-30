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
    domain_interests = models.ManyToManyField(
        "assessment.AssessmentInterestCategory",
        blank=True,
        related_name="student_profiles",
    )
    career_direction = models.JSONField(default=list, blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    skills = models.JSONField(default=list, null=True, blank=True)
    projects = models.JSONField(default=list, null=True,blank=True)
    internships = models.JSONField(default=list, null=True, blank=True)
    certifications = models.JSONField(default=list, null=True, blank=True)
    achievements = models.JSONField(default=list, null=True, blank=True)
    extra_activities = models.JSONField(default=list, null=True, blank=True)
    additional_insights = models.JSONField(default=list, null=True, blank=True)
    linkedin_url = models.CharField(max_length=200, null=True, blank=True)
    github_url = models.CharField(max_length=200, null=True, blank=True)
    portfolio = models.CharField(max_length=200, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"StudentProfile<{self.user_id}>"

    class Meta:
        db_table = "student_profile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["education_level"]),
            models.Index(fields=["stream"]),
            models.Index(fields=["science_track"]),
            models.Index(fields=["medium"]),
        ]


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
    

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="professional_profile",
    )

    language = models.ManyToManyField(
        "language_master.Language",           
        blank=True,
        related_name="professional_profiles",
        help_text="Preferred languages selected from Language master",
    )

    class EmploymentType(models.TextChoices):
        SALARIED = "salaried_employee", "Salaried Employee"
        SELF_EMPLOYED = "self_employed", "Self-employed / Business Owner"
        FREELANCER = "freelancer", "Freelancer"
        JOB_SEEKER = "job_seeker", "Looking for first job"

    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        null=True,
        blank=True,
        help_text="Current employment status"
    )

    class ExperienceRange(models.TextChoices):
        ZERO_TO_ONE = "0-1", "0-1 years"
        ONE_TO_THREE = "1-3", "1-3 years"
        THREE_TO_FIVE = "3-5", "3-5 years"
        FIVE_TO_TEN = "5-10", "5-10 years"
        TEN_PLUS = "10+", "10+ years"

    years_of_experience = models.CharField(
        max_length=10,
        choices=ExperienceRange.choices,
        null=True,
        blank=True,
        help_text="Years of professional experience"
    )

    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professional_profiles",
    )

    current_job_title = models.CharField(max_length=150, null=True, blank=True)
    current_industry = models.CharField(max_length=100, null=True, blank=True)
    company_size = models.CharField(max_length=50, null=True, blank=True)

    # JSONField sections for professional profile
    career_direction = models.JSONField(default=list, blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    work_experience = models.JSONField(default=list, null=True, blank=True)
    skills = models.JSONField(default=list, null=True, blank=True)
    certifications = models.JSONField(default=list, null=True, blank=True)
    key_highlights = models.JSONField(default=list, null=True, blank=True)
    additional_insights = models.JSONField(default=list, null=True, blank=True)

    # Professional links
    linkedin_url = models.CharField(max_length=200, null=True, blank=True)
    github_url = models.CharField(max_length=200, null=True, blank=True)
    portfolio = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ProfessionalProfile<{self.user_id}>"

    class Meta:
        db_table = "professional_profile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["education_level"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["years_of_experience"]),
        ]


class ParentProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="parent_profile",
        
    )

    language = models.ManyToManyField(
        "language_master.Language",
        blank=True,
        related_name="parent_profiles",
    )

    class Relationship(models.TextChoices):
        MOTHER = "mother", "Mother"
        FATHER = "father", "Father"
        GUARDIAN = "guardian", "Guardian"
        OTHER = "other", "Other"

    relationship = models.CharField(
        max_length=20,
        choices=Relationship.choices,
        null=True,
        blank=True,
    )

    child_name = models.CharField(max_length=150, null=True, blank=True)
    child_education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profiles",
    )
    stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_profiles",
    )
    academic_performance = models.CharField(
        max_length=50,
        choices=[
            ("average", "Average"),
            ("good", "Good"),
            ("excellent", "Excellent"),
        ],
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ParentProfile<{self.user_id}>"

    class Meta:
        db_table = "parent_profile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["child_education_level"]),
            models.Index(fields=["stream"]),
        ]


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
