from django.conf import settings
from django.db import models

from common.models import BaseModule


class Question(models.Model):
    class Dimension(models.TextChoices):
        INTEREST = "interest", "Interest"
        APTITUDE = "aptitude", "Aptitude"
        PERSONALITY = "personality", "Personality"
        WORK_STYLE = "work_style", "Work Style"

    class QuestionType(models.TextChoices):
        SCALE = "scale", "Scale (1-5 agreement)"
        MCQ = "mcq", "Multiple Choice (pick one)"
        YESNO = "yesno", "Yes / No"

    question_text = models.TextField()
    dimension = models.CharField(max_length=20, choices=Dimension.choices)
    question_type = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        default=QuestionType.SCALE,
        help_text="Controls how options are presented to the user.",
    )
    sequence_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order within the same education level and signal type.",
    )
    mapped_domains = models.ManyToManyField(
        "domain.Domain",
        related_name="assessment_questions",
        blank=True,
    )
    signal_strength = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    # Education-level aware filtering
    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_questions",
        help_text="If set, this question is only shown to users at this education level.",
    )
    # For 12th-grade users: optionally restrict question to a specific stream
    target_stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessment_questions",
        db_column="stream_id",
        help_text="If set, this question is only shown to 12th-grade users who selected this stream.",
    )
    # For 10th-grade users: which streams does a positive answer signal?
    mapped_streams = models.ManyToManyField(
        "stream.Stream",
        related_name="signal_questions",
        blank=True,
        help_text="Streams this question signals affinity for (used for 10th-grade stream recommendations).",
    )

    class Meta:
        db_table = "assessment_question"
        ordering = ["education_level", "sequence_order", "id"]

    def __str__(self):
        return f"[{self.dimension}] {self.question_text[:60]}"


class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    option_text = models.CharField(max_length=255)
    sequence_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order of this option within its question.",
    )

    class Meta:
        db_table = "assessment_option"
        ordering = ["sequence_order", "id"]

    def __str__(self):
        return f"Q{self.question_id} - {self.option_text[:40]}"


class UserResponse(models.Model):
    assessment = models.ForeignKey(
        "assessment.StudentAssessment",
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_responses",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="responses",
    )
    selected_option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name="responses",
        null=True,
        blank=True,
        default=None,
    )

    class Meta:
        db_table = "assessment_user_response"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "question"],
                name="assessment_question_unique",
            ),
        ]

    def __str__(self):
        return f"user={self.user_id}, question={self.question_id}, option={self.selected_option_id}"


class Concern(BaseModule):
    name = models.CharField(max_length=150)
    
    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = "assessment_concern"

class CareerValue(BaseModule):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = "assessment_career_value"

class UserGoal(BaseModule):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = "assessment_usergoal"

class CareerDirection(BaseModule):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        db_table = "assessment_career_direction"


class ParentCareerExpectation(BaseModule):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "assessment_parent_career_expectation"


class ParentConstraint(BaseModule):
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = "assessment_parent_constraint"

class GuidanceReason(BaseModule):          
    name = models.CharField(max_length=150)
 
    def __str__(self):
        return self.name
 
    class Meta:
        db_table = "assessment_guidance_reason"
 
 
class WorkConstraint(BaseModule):          
    name = models.CharField(max_length=150)
 
    def __str__(self):
        return self.name
 
    class Meta:
        db_table = "assessment_work_constraint"

class StudentAssessment(BaseModule):
    class Screen(models.TextChoices):
        EDUCATION_LEVEL = "education_level", "Education Level"
        STREAM = "stream", "Stream / Path"
        DOMAIN_CATEGORY = "domain_category", "Domain Category"
        DOMAIN = "domain", "Domain"
        CAREER_DIRECTION = "career_direction", "Career Direction"
        PARENT_SUPPORT = "parent_support", "Parent Support"
        CONCERNS = "concerns", "Concerns"
        INTEREST = "interest", "Interest Questions"
        APTITUDE = "aptitude", "Aptitude Questions"
        PERSONALITY = "personality", "Personality Questions"
        WORK_STYLE = "work_style", "Work Style Questions"
        CAREER_VALUES = "career_values", "Career Values"
        USER_GOALS = "user_goals", "User Goals"
        COMPLETE = "complete", "Complete"

    PARENT_CHOICES = (
        ("very_supportive", "Very Supportive"),
        ("somewhat_supportive", "SomeWhat Supportive"),
        ("neutral", "Neutral"),
        ("not_supportive", "Not Supportive"),
        ("notsure", "Not Sure"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_assessments",
    )
    domain_category = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="category_assessments",
        help_text="Parent category domain selected by the student.",
    )
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        help_text="Child domain selected by the student.",
    )
    parent_support = models.CharField(
        choices=PARENT_CHOICES, max_length=150, null=True, blank=True
    )
    concerns = models.ManyToManyField(Concern, blank=True)
    career_direction = models.ManyToManyField(CareerDirection, blank=True)
    career_values = models.ManyToManyField(CareerValue, blank=True)
    user_goals = models.ManyToManyField(UserGoal, blank=True)
    current_screen = models.CharField(
        max_length=32,
        choices=Screen.choices,
        default=Screen.EDUCATION_LEVEL,
    )
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "student_assessment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Assessment {self.id} - User {self.user_id}"


class ParentAssessment(BaseModule):
    class Screen(models.TextChoices):
        DOMAIN_CATEGORY = "domain_category", "Domain Category"
        DOMAIN = "domain", "Domain"
        CAREER_DIRECTION = "career_direction", "Career Direction"
        PARENT_SUPPORT = "parent_support", "Parent Support"
        CONCERNS = "concerns", "Concerns"
        PARENT_CAREER_EXPECTATIONS = "parent_career_expectations", "Parent Career Expectations"
        LIMITATIONS = "limitations", "Limitations"
        CAREER_FAMILIARITY = "career_familiarity", "Career Familiarity"
        DECISION_STYLE = "decision_style", "Decision Style"
        CAREER_VALUES = "career_values", "Career Values"
        USER_GOALS = "user_goals", "User Goals"
        COMPLETE = "complete", "Complete"

    PARENT_SUPPORT_CHOICES = (
        ("very_supportive", "Very Supportive"),
        ("somewhat_supportive", "SomeWhat Supportive"),
        ("neutral", "Neutral"),
        ("not_supportive", "Not Supportive"),
        ("notsure", "Not Sure"),
    )

    FAMILIARITY_CHOICES = (
        ("very_aware", "Very Aware"),
        ("somewhat_aware", "Somewhat Aware"),
        ("limited_knowledge", "Limited Knowledge"),
        ("not_aware", "Not Aware"),
    )

    DECISION_STYLE_CHOICES = (
        ("stability_based", "Stability Based"),
        ("interest_based", "Interest Based"),
        ("income_based", "Income Based"),
        ("family_advice_based", "Family Advice Based"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_assessments",
    )
    child = models.ForeignKey(
        "user_profile.ChildProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_assessments",
        help_text="The child this assessment is about.",
    )
    domain_category = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_category_assessments",
        help_text="Parent category domain selected by the parent.",
    )
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_domain_assessments",
        help_text="Child domain selected by the parent.",
    )
    career_direction = models.ManyToManyField(CareerDirection, blank=True)
    parent_support = models.CharField(
        max_length=50,
        choices=PARENT_SUPPORT_CHOICES,
        null=True,
        blank=True,
    )
    concerns = models.ManyToManyField(Concern, blank=True)
    parent_career_expectations = models.ManyToManyField(ParentCareerExpectation, blank=True)
    limitations = models.ManyToManyField(ParentConstraint, blank=True)
    career_familiarity = models.CharField(
        max_length=50,
        choices=FAMILIARITY_CHOICES,
        null=True,
        blank=True,
    )
    decision_style = models.CharField(
        max_length=50,
        choices=DECISION_STYLE_CHOICES,
        null=True,
        blank=True,
    )
    career_values = models.ManyToManyField(CareerValue, blank=True)
    user_goals = models.ManyToManyField(UserGoal, blank=True)
    current_screen = models.CharField(
        max_length=50,
        choices=Screen.choices,
        default=Screen.DOMAIN_CATEGORY,
    )
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = "parent_assessment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["current_screen"]),
        ]

    def __str__(self):
        return f"ParentAssessment {self.id} - User {self.user_id}"

class ProfessionalAssessment(BaseModule):
    class CareerIntention(models.TextChoices):   
        CAREER_CHANGE = "career_change", "Career Change"
        PROMOTION_GROWTH = "promotion_growth", "Promotion / Growth"
        UPSKILL = "upskill_learn_new_skills", "Upskill / Learn New Skills"
        START_BUSINESS = "start_own_business", "Start Own Business"
        FIND_JOB = "find_a_job", "Find a Job"
        NOT_SURE = "not_sure_yet", "Not Sure Yet"
 
    class WorkEnvironment(models.TextChoices):      
        REMOTE = "remote_work_from_home", "Remote / Work from Home"
        HYBRID = "hybrid_office_and_remote", "Hybrid (Office & Remote)"
        OFFICE = "office_based", "Office Based"
        FIELD = "field_work_travel", "Field Work / Travel"
 
    class WorkStructure(models.TextChoices):       
        FIXED = "fixed_9_6_schedule", "Fixed 9-6 Schedule"
        FLEXIBLE = "flexible_hours", "Flexible Hours"
        PROJECT = "project_based", "Project Based"
        FREELANCE = "freelance_contract", "Freelance / Contract"
 
    class Screen(models.TextChoices):               
        CAREER_INTENTION = "career_intention", "Career Intention"
        GUIDANCE_REASON = "guidance_reason", "Guidance Reason"
        WORK_CONSTRAINT = "work_constraint", "Work Constraint"
        WORK_STYLE = "work_style", "Work Style"
        DOMAIN_CATEGORY = "domain_category", "Domain Category"
        DOMAIN = "domain", "Domain"
        CAREER_VALUES = "career_values", "Career Values"         
        SALARY = "salary", "Salary Expectations"                 
        TIMELINE = "timeline", "Timeline"                        
        PLATFORM_GOALS = "platform_goals", "Platform Goals"       
        COMPLETE = "complete", "Complete"
    
    class SalaryExpectation(models.TextChoices):
        THREE_TO_FIVE= "3_5_lakhs_per_year", "3-5 lakhs per year"
        FIVE_TO_EIGHT= "5_8_lakhs_per_year", "5-8 lakhs per year"
        EIGHT_TO_FIFTEEN = "8_15_lakhs_per_year", "8-15 Lakhs per year"
        FIFTEEN_TO_TWENTYFIVE = "15_25_lakhs_per_year", "15-25 Lakhs per year"
        TWENTYFIVE_PLUS = "25_plus_lakhs_per_year", "25+ Lakhs per year"
        NOT_SURE = "not_sure_open_to_discussion", "Not Sure / Open to Discussion"

    class Timeline(models.TextChoices):
        IMMEDIATELY = "immediately_within_3_months", "Immediately (within 3 months)"
        WITHIN_6_MONTHS = "within_6_months", "Within 6 months"
        WITHIN_1_YEAR = "within_1_year", "Within 1 year"
        EXPLORING = "exploring_options_no_rush", "Exploring options, no rush"
        NOT_SURE = "not_sure_yet", "Not Sure Yet"
 
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_assessments",
    )
 
    career_intention = models.CharField(
        max_length=50,
        choices=CareerIntention.choices,
        null=True, blank=True,
    )
 
    guidance_reasons = models.ManyToManyField(GuidanceReason, blank=True)

    work_constraints = models.ManyToManyField(WorkConstraint, blank=True)
 
    preferred_environment = models.CharField(
        max_length=50,
        choices=WorkEnvironment.choices,
        null=True, blank=True,
    )
    preferred_structure = models.CharField(
        max_length=50,
        choices=WorkStructure.choices,
        null=True, blank=True,
    )
 
    domain_category = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="professional_category_assessments",
        help_text="Parent domain category selected by the professional.",
    )
    domain = models.ForeignKey(
        "domain.Domain",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="professional_assessments",
        help_text="Child domain selected by the professional.",
    )

    career_values = models.ManyToManyField(CareerValue, blank=True)
    salary_expectation = models.CharField(
        max_length=50, choices=SalaryExpectation.choices,
        null=True, blank=True,
    )
    timeline = models.CharField(
        max_length=50, choices=Timeline.choices,
        null=True, blank=True
    )

    platform_goals = models.ManyToManyField(UserGoal, blank=True)
 
    current_screen = models.CharField(
        max_length=32,
        choices=Screen.choices,
        default=Screen.CAREER_INTENTION,
    )
    is_completed = models.BooleanField(default=False)
 
    class Meta:
        db_table = "professional_assessment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["current_screen"]),
        ]
 
    def __str__(self):
        return f"ProfessionalAssessment {self.id} - User {self.user_id}"