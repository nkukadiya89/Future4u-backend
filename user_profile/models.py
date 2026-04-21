from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.timezone import now

from city.models import City
from company.models import Company
from country.models import Country
from domain.models import Domain
from skill.models import Skill
from state.models import State


class UserProfile(models.Model):

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

    class CareerGoal(models.TextChoices):
        STUDY_FURTHER = "study_further", "Study Further"
        FIND_JOB = "find_job", "Find a Job"
        INTERNSHIP = "internship", "Internship"
        SKILL_DEVELOPMENT = "skill_development", "Skill Development"
        NOT_SURE = "not_sure", "Not Sure Yet"

    career_goal = ArrayField(
        models.CharField(max_length=50, choices=CareerGoal.choices),
        default=list,
        null=True,
        blank=True,
    )

    class ScienceTrack(models.TextChoices):
        PCM = "pcm", "PCM (Physics, Chemistry, Maths)"
        PCB = "pcb", "PCB (Physics, Chemistry, Biology)"
        PCMB = "pcmb", "PCMB (All four)"

    science_track = models.CharField(
        max_length=10,
        choices=ScienceTrack.choices,
        null=True,
        blank=True,
    )

    class ParentSupportLevel(models.TextChoices):
        VERY_SUPPORTIVE = "very_supportive", "Very Supportive"
        SOMEWHAT_SUPPORTIVE = "somewhat_supportive", "Somewhat Supportive"
        NEUTRAL = "neutral", "Neutral"
        SOMEWHAT_RESTRICTIVE = "somewhat_restrictive", "Somewhat Restrictive"
        VERY_RESTRICTIVE = "very_restrictive", "Very Restrictive"

    parent_support_level = models.CharField(
        max_length=25,
        choices=ParentSupportLevel.choices,
        null=True,
        blank=True,
    )

    class CareerValue(models.TextChoices):
        HIGH_SALARY = "high_salary_potential", "High Salary Potential"
        JOB_SECURITY = "job_security_stability", "Job Security and Stability"
        CREATIVITY = "creativity_innovation", "Creativity and Innovation"
        WORK_LIFE_BALANCE = "work_life_balance", "Work Life Balance"
        SOCIAL_IMPACT = "social_impact", "Making an Impact on Society"
        GROWTH = "growth_and_learning", "Opportunities to Grow and Learn"

    career_values = ArrayField(
        models.CharField(max_length=50, choices=CareerValue.choices),
        default=list,
        null=True,
        blank=True,
    )

    class PlatformGoal(models.TextChoices):
        CAREER_CLARITY = "career_clarity", "Career Clarity"
        COURSE_RECOMMENDATIONS = "course_recommendations", "Course Recommendations"
        JOB_INTERNSHIP = (
            "job_internship_opportunities",
            "Job / Internship Opportunities",
        )
        PARENT_CONFIDENCE = "parent_confidence", "Parent Confidence"

    platform_goals = ArrayField(
        models.CharField(max_length=50, choices=PlatformGoal.choices),
        default=list,
        null=True,
        blank=True,
    )

    class InterestCategory(models.TextChoices):
        TECHNOLOGY = "technology", "Technology / Coding"
        HEALTHCARE = "healthcare", "Healthcare"
        BUSINESS_MANAGEMENT = "business_management", "Business Management"
        AGRICULTURE = "agriculture", "Agriculture / Food"
        CREATIVE_DESIGN = "creative_design", "Creative / Design"
        SPORTS_FITNESS = "sports_fitness", "Sports / Fitness"
        GOVERNMENT = "government", "Government / Public Service"
        ENGINEERING = "engineering", "Engineering"
        FINANCE = "finance", "Finance"
        EDUCATION = "education", "Education"
        LAW = "law", "Law"
        SCIENCE_RESEARCH = "science_research", "Science & Research"
        SOCIAL_WELFARE = "social_welfare", "Social Welfare"
        HOSPITALITY = "hospitality", "Hospitality"
        VOCATIONAL = "vocational", "Vocational / Trades"

    interest_categories = ArrayField(
        models.CharField(max_length=50, choices=InterestCategory.choices),
        default=list,
        null=True,
        blank=True,
        help_text="Broad interest categories e.g. ['technology', 'healthcare', 'government']",
    )

    class UserConcern(models.TextChoices):
        JOB_SECURITY = "job_security", "Job Security"
        FUTURE_DEMAND = "future_demand", "Future Demand"
        WRONG_CHOICE = "wrong_career_choice", "Wrong Career Choice"
        EDUCATION_COST = "high_education_cost", "High Education Cost"
        LIMITED_GUIDANCE = "limited_guidance", "Limited Guidance"

    user_concerns = ArrayField(
        models.CharField(max_length=50, choices=UserConcern.choices),
        default=list,
        null=True,
        blank=True,
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
    country = models.ForeignKey(
        Country,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )
    city = models.ForeignKey(
        City,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )
    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )
    stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
    )

    def __str__(self):
        return f"Profile<{self.user_id}>"

    class Meta:
        db_table = "user_profile"


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

    title = models.CharField(max_length=150)  # "Career Switch Plan", etc.

    # Location
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


class InternshipProfile(models.Model):
    profile = models.OneToOneField(
        Profile, on_delete=models.CASCADE, related_name="internship"
    )

    domains = models.ManyToManyField(Domain, blank=True)

    current_degree = models.CharField(max_length=150, null=True, blank=True)
    college_name = models.CharField(max_length=200, null=True, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)

    experience_level = models.CharField(
        max_length=50,
        choices=(
            ("fresher", "Fresher"),
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
        ),
        default="fresher",
    )

    available_from = models.DateField(null=True, blank=True)
    duration_weeks = models.IntegerField(null=True, blank=True)

    preferred_work_mode = models.CharField(max_length=50, null=True, blank=True)
    expected_stipend = models.CharField(max_length=50, null=True, blank=True)

    resume = models.FileField(upload_to="resumes/", null=True, blank=True)
    portfolio_link = models.URLField(null=True, blank=True)
    github_link = models.URLField(null=True, blank=True)

    why_internship = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="internship_profile_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_profile_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Internship<{self.id} - {self.profile.title}>"

    class Meta:
        db_table = "internship_profile"
        ordering = ["-created_at"]


class InternshipProfileSkill(models.Model):
    LEVEL_CHOICES = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    )

    internship_profile = models.ForeignKey(
        InternshipProfile, on_delete=models.CASCADE, related_name="skill_map"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    years_of_experience = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="internship_skill_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_skill_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"InternshipSkill<{self.id} - {self.internship_profile.profile.title} - {self.skill.name}>"

    class Meta:
        db_table = "internship_profile_skill"
        ordering = ["-created_at"]
        unique_together = ("internship_profile", "skill")


class InternshipApplication(models.Model):
    STATUS_CHOICES = (
        ("applied", "Applied"),
        ("shortlisted", "Shortlisted"),
        ("rejected", "Rejected"),
        ("accepted", "Accepted"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    internship_profile = models.ForeignKey(InternshipProfile, on_delete=models.CASCADE)

    company_name = models.CharField(max_length=200)
    role = models.CharField(max_length=150)

    cover_letter = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")

    applied_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="internship_application_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_application_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"InternshipApplication<{self.id} - {self.internship_profile.profile.title} - {self.user.username}>"

    class Meta:
        db_table = "internship_application"
        ordering = ["-created_at"]
