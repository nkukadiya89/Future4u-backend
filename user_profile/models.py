import os

from django.conf import settings
from django.db import models
from common.models import BaseModule
from city.models import City
from company.models import Company
from country.models import Country
from state.models import State
from education_level.models import EducationLevel
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket
from django.core.exceptions import ValidationError



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

    medium = models.CharField(
        max_length=20,
        choices=[
            ("english", "English"),
            ("hindi", "Hindi"),
            ("gujarati", "Gujarati"),
            ("marathi", "Marathi"),
            ("tamil", "Tamil"),
            ("telugu", "Telugu"),
            ("kannada", "Kannada"),
            ("bengali", "Bengali"),
            ("punjabi", "Punjabi"),
            ("odia", "Odia"),
            ("malayalam", "Malayalam"),
            ("urdu", "Urdu"),
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
    career_direction = models.JSONField(default=list, blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    skills = models.JSONField(default=list, null=True, blank=True)
    projects = models.JSONField(default=list, null=True, blank=True)
    internships = models.JSONField(default=list, null=True, blank=True)
    certifications = models.JSONField(default=list, null=True, blank=True)
    achievements = models.JSONField(default=list, null=True, blank=True)
    extra_activities = models.JSONField(default=list, null=True, blank=True)
    additional_insights = models.JSONField(default=list, null=True, blank=True)
    linkedin_url = models.CharField(max_length=200, null=True, blank=True)
    github_url = models.CharField(max_length=200, null=True, blank=True)
    portfolio = models.CharField(max_length=200, null=True, blank=True)
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_students")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"StudentProfile<{self.user_id}>"

    class Meta:
        db_table = "student_profile"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["education_level"]),
            models.Index(fields=["stream"]),
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
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="business_setting_updated",
    )
    updated_at = models.DateTimeField(auto_now=True, null=True)

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
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profile_updated",
    )
    updated_at = models.DateTimeField(auto_now=True, null=True)

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
        SELF_EMPLOYED = "self_employed_business_owner", "Self Employed / Business Owner"
        FREELANCER = "freelancer", "Freelancer"
        JOB_SEEKER = "looking_for_first_job", "Looking for first job"
        OTHER = "other", "Other"

    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        null=True,
        blank=True,
        help_text="Current employment status",
    )

    employment_type_other_text = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    current_industry_category = models.ForeignKey(
         "domain.Domain",
         on_delete=models.SET_NULL,
         null=True,
         blank=True,
         related_name="current_industry_category_profiles",
    )

    current_industry = models.ForeignKey(
        "domain.Domain",
         on_delete=models.SET_NULL,
         null=True,
         blank=True,
         related_name="current_industry_profiles",
    )

    class CompanySize(models.TextChoices):
        STARTUP = "startup_1_50", "Startup (1–50)"
        SMALL = "small_51_200", "Small (51–200)"
        MEDIUM = "medium_201_1000", "Medium (201–1000)"
        LARGE = "large_1000_plus", "Large (1000+)"

    company_size = models.CharField(
        max_length=30,
        choices=CompanySize.choices,
        null=True,
        blank=True
    )
 
    class ExperienceRange(models.TextChoices):
        ZERO_TO_ONE = "0_1_years", "0–1 years"
        ONE_TO_THREE = "1_3_years", "1–3 years"
        THREE_TO_FIVE = "3_5_years", "3–5 years"
        FIVE_PLUS = "5_plus_years", "5+ years"
    
    

    years_of_experience = models.CharField(
        max_length=20,
        choices=ExperienceRange.choices,
        null=True,
        blank=True,
        help_text="Years of professional experience",
    )

    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="professional_profiles",
    )

    stream = models.ForeignKey(
    "stream.Stream",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="professional_profiles",
    )

    def clean(self):
       super().clean()

       if self.employment_type != self.EmploymentType.OTHER:
           self.employment_type_other_text = None

       if (
           self.employment_type == self.EmploymentType.OTHER
           and not self.employment_type_other_text
    ):
           raise ValidationError({
             "employment_type_other_text": "Please specify the employment type."
    })

       category = self.current_industry_category
       industry = self.current_industry

       if category and category.parent_id is not None:
           raise ValidationError({
                "current_industry_category": "Must be a parent domain"
           })

       if industry and industry.parent_id is None:
           raise ValidationError({
                "current_industry": "Must be a child domain"
           })

       if category and industry and industry.parent_id != category.id:
           raise ValidationError({
                "current_industry": "Must belong to selected category"
           })
       

    current_job_title = models.CharField(max_length=150, null=True, blank=True)

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
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_professionals")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f"ProfessionalProfile<{self.user_id}>"

    class Meta:
        db_table = "professional_profile"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["education_level"]),
            models.Index(fields=["employment_type"]),
            models.Index(fields=["years_of_experience"]),
            models.Index(fields=["current_industry_category"]),
            models.Index(fields=["current_industry"]),
            models.Index(fields=["stream"]),
        ]


class ParentProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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
    other_relationship_text = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Custom relationship text when 'other' is selected",
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
        ]


class ChildProfile(models.Model):
    """A child managed by a parent, linked to the parent's profile."""

    class AcademicPerformance(models.TextChoices):
        AVERAGE = "average", "Average"
        GOOD = "good", "Good"
        EXCELLENT = "excellent", "Excellent"

    parent_profile = models.ForeignKey(
        ParentProfile,
        on_delete=models.CASCADE,
        related_name="children",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    profile_image = models.CharField(max_length=250, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    education_level = models.ForeignKey(
        "education_level.EducationLevel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_profiles",
    )
    stream = models.ForeignKey(
        "stream.Stream",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_profiles",
    )
    academic_performance = models.CharField(
        max_length=20,
        choices=AcademicPerformance.choices,
    )

    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    language = models.ManyToManyField(
        "language_master.Language",
        blank=True,
        related_name="child_profiles",
    )
    career_direction = models.JSONField(default=list, blank=True, null=True)
    education = models.JSONField(default=list, blank=True, null=True)
    skills = models.JSONField(default=list, null=True, blank=True)
    projects = models.JSONField(default=list, null=True, blank=True)
    internships = models.JSONField(default=list, null=True, blank=True)
    certifications = models.JSONField(default=list, null=True, blank=True)
    achievements = models.JSONField(default=list, null=True, blank=True)
    extra_activities = models.JSONField(default=list, null=True, blank=True)
    additional_insights = models.JSONField(default=list, null=True, blank=True)
    preferred_job_locations = models.JSONField(default=list, blank=True, null=True)
    linkedin_url = models.CharField(max_length=200, null=True, blank=True)
    github_url = models.CharField(max_length=200, null=True, blank=True)
    portfolio = models.CharField(max_length=200, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def upload_profile_image(self, profile_image_file):
        import os

        from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket

        allowed_types = [".jpg", ".jpeg", ".png"]
        file_extension = os.path.splitext(profile_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            raise ValueError(
                f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."
            )
        current_value = getattr(self, "profile_image", None)
        try:
            if current_value:
                delete_uploaded_file(current_value)
            aws_file_url, _ = upload_file_to_bucket(
                profile_image_file,
                allowed_types,
                "ProfileImage/",
                self.id,
                None,
            )
            self.profile_image = aws_file_url
            self.save(update_fields=["profile_image"])
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload profile image: {str(e)}")

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    class Meta:
        db_table = "parent_child_profile"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["parent_profile"]),
            models.Index(fields=["education_level"]),
            models.Index(fields=["stream"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parent_profile", "first_name", "last_name", "date_of_birth"],
                condition=models.Q(deleted=False),
                name="unique_active_child_per_parent",
            ),
        ]


class InstituteProfile(BaseModule):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="institute_profile")
    student_trained = models.PositiveIntegerField(null=True, blank=True)
    placements = models.PositiveIntegerField(null=True, blank=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    about_us = models.TextField(null=True, blank=True)
    courses_offered = models.JSONField(default=list, blank=True)
    key_highlights = models.JSONField(default=list, blank=True)
    website = models.CharField(max_length=250, null=True, blank=True)
    institute_name = models.CharField(max_length=200, null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "institute_profile"
        ordering = ["-id"]


def _upload_organization_gallery_image(instance, image, upload_folder):
    allowed_types = [".jpg", ".jpeg", ".png"]

    file_extension = os.path.splitext(image.name)[1].lower()
    if file_extension not in allowed_types:
        raise ValueError(
            f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."
        )

    if image.size > 5 * 1024 * 1024:
        raise ValueError("Image size exceeds 5MB limit.")

    current_value = getattr(instance, "image", None)

    try:
        if current_value:
            delete_uploaded_file(current_value)

        aws_file_url, _ = upload_file_to_bucket(
            image,
            allowed_types,
            upload_folder,
            instance.id,
            None,
        )
        instance.image = aws_file_url
        instance.save(update_fields=["image"])
    except ValueError:
        raise
    except Exception as e:
        raise Exception(f"Failed to upload profile image: {str(e)}")


class InstituteGallery(BaseModule):
    institute = models.ForeignKey(InstituteProfile, on_delete=models.CASCADE, related_name="gallery_images")
    image = models.CharField(max_length=350, null=True, blank=True)

    class Meta:
        db_table = "institute_gallery"
        ordering = ["-created_at"]

    def upload_gallery_image(self, image):
        _upload_organization_gallery_image(self, image, "InstituteGallery/")


class SchoolCollegeProfile(BaseModule):

    TOTAL_STUDENT = (
        ("under_500","Under 500"),
        ("500_1000","500-1000"),
        ("1000_3000","1000-3000"),
        ("above_3000","3000+"),
    )
    READINESS = (
        ("immediately", "Immediately"),
        ("within_1month", "Within 1 month"),
        ("within_3month", "Within 3 month"),
        ("flexible_timeline", "Flexible timeline"),
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_college_profile",
    )
    student_trained = models.PositiveIntegerField(null=True, blank=True)
    placements = models.PositiveIntegerField(null=True, blank=True)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    about_us = models.TextField(null=True, blank=True)
    courses_offered = models.JSONField(default=list, blank=True)
    education  = models.ManyToManyField(EducationLevel, blank=True, related_name="school_college_profiles")
    institute_name = models.CharField(max_length=200, null=True, blank=True)
    total_student = models.CharField(max_length=50, choices=TOTAL_STUDENT, default="under_500")
    board = models.CharField(max_length=200, null=True, blank=True)
    partnership_readiness = models.CharField(max_length=50, choices=READINESS, default="flexible_timeline")
    website = models.CharField(max_length=250, null=True, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "school_college_profile"
        ordering = ["-created_at"]

    def get_education_names(self):
        return list(self.education.values_list("display_name", flat=True))


class SchoolCollegeGallery(BaseModule):
    school_college = models.ForeignKey(
        SchoolCollegeProfile, on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.CharField(max_length=350, null=True, blank=True)

    class Meta:
        db_table = "school_college_gallery"
        ordering = ["-created_at"]

    def upload_gallery_image(self, image):
        _upload_organization_gallery_image(self, image, "SchoolCollegeGallery/")


class CorporateProfile(BaseModule):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="corporate_profile",
    )
    website = models.CharField(max_length=250, null=True, blank=True)
    company_name = models.CharField(max_length=200, null=True, blank=True)
    open_job = models.PositiveIntegerField(null=True, blank=True)
    employees = models.PositiveIntegerField(null=True, blank=True)
    years_in_business = models.PositiveIntegerField(null=True, blank=True)
    about_us = models.TextField(null=True, blank=True)
    perks_benefits = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "corporate_profile"
        ordering = ["-created_at"]


class CorporateGallery(BaseModule):
    corporate = models.ForeignKey(
        CorporateProfile, on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.CharField(max_length=350, null=True, blank=True)

    class Meta:
        db_table = "corporate_gallery"
        ordering = ["-created_at"]

    def upload_gallery_image(self, image):
        _upload_organization_gallery_image(self, image, "CorporateGallery/")
