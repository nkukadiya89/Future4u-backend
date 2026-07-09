from django.db import models
from common.models import BaseModule
from city.models import City
from country.models import Country
from state.models import State
from django.conf import settings
from education_level.models import EducationLevel
from user.models import User
from user_profile.models import CorporateProfile
import os

from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


# Create your models here.
class Internship(BaseModule):

    INTERNSHIP_TYPE_CHOICES = (
        ("free", "Free"),
        ("paid", "Paid"),
        ("stipend", "Stipend"),
    )

    MODE_CHOICE = (
        ("online", "Online"),
        ("offline", "Offline"),
    )

    name = models.CharField(max_length=250, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    organization_name = models.CharField(max_length=250, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    education_tags = models.ManyToManyField(EducationLevel, blank=True)
    why_this_match = models.TextField(null=True, blank=True)
    internship_type = models.CharField(
        max_length=150, choices=INTERNSHIP_TYPE_CHOICES, default="free"
    )
    mode = models.CharField(max_length=150, choices=MODE_CHOICE, default="offline")
    duration = models.CharField(max_length=150, null=True, blank=True)
    fees_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stipend_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    certificate_provided = models.BooleanField(default=True)
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internships",
    )

    class Meta:
        db_table = "internship"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class InternshipApplication(BaseModule):

    APPLICATION_STATUS_CHOICE = (
        ("applied", "Applied"),
        ("under_review", "Under_Review"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
    )

    applicant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_internship_applications",
    )
    internship = models.ForeignKey(
        Internship,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internship_applications",
    )
    resume = models.CharField(max_length=450, null=True, blank=True)
    status = models.CharField(
        max_length=100, choices=APPLICATION_STATUS_CHOICE, default="applied"
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "internship_application"
        ordering = ["-created_at"]

    def upload_resume(self, resume_file):
        allowed_type = [".pdf", ".docs", ".docx"]

        file_extension = os.path.splitext(resume_file.name)[1].lower()

        if file_extension not in allowed_type:
            raise ValueError(f"Invalid file type: {file_extension}")

        current_value = getattr(self, "resume_file", None)
        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, presigned_url = upload_file_to_bucket(
                resume_file,
                allowed_type,
                "InternshipResume/",
                str(self.id),
                None,
            )

            self.resume = aws_file_url
            self.save(update_fields=["resume"])
            return aws_file_url
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload resume: {str(e)}")


class Job(BaseModule):

    JOB_TYPE_CHOICE = (
        ("part_time", "Part Time"),
        ("full_time", "Full Time"),
        ("freelance", "Freelance"),
    )

    EXPERIENCE_CHOICES = (
        ("fresher", "Fresher"),
        ("0_1", "0-1 Years"),
        ("1_3", "1-3 Years"),
        ("3_5", "3-5 Years"),
        ("5_10", "5-10 Years"),
        ("10_plus", "10+ Years"),
    )
    MODE_CHOICES = (
        ("remote", "Remote"),
        ("onsite", "Onsite"),
        ("hybrid", "Hybrid"),
    )

    JOB_STATUS_CHOICE = (
        ("draft", "Draft"),
        ("active", "Active"),
        ("closed", "Closed"),
    )

    name = models.CharField(max_length=250, null=True, blank=True)
    corporate = models.ForeignKey(CorporateProfile,on_delete=models.CASCADE,related_name="jobs",null=True,blank=True)
    job_overview = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    skills = models.JSONField(default=list, blank=True)
    education_tags = models.ManyToManyField(EducationLevel, blank=True)
    experience_level = models.CharField(
        max_length=100, choices=EXPERIENCE_CHOICES, default="fresher"
    )
    job_type = models.CharField(
        max_length=100, choices=JOB_TYPE_CHOICE, default="full_time"
    )
    mode = models.CharField(max_length=100, choices=MODE_CHOICES, default="onsite")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True, blank=True)
    state = models.ForeignKey(State, on_delete=models.CASCADE, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    salary_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    salary_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobs",
    )
    why_this_match = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=100, choices=JOB_STATUS_CHOICE, default="draft")

    class Meta:
        db_table = "jobs"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class JobApplication(BaseModule):

    APPLICATION_STATUS_CHOICE = (
        ("applied", "Applied"),
        ("under_review", "Under_Review"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
    )

    applicant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_job_applications",
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_applications",
    )
    resume = models.CharField(max_length=450, null=True, blank=True)
    status = models.CharField(
        max_length=150, choices=APPLICATION_STATUS_CHOICE, default="applied"
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "job_application"
        ordering = ["-created_at"]

    def upload_resume(self, resume_file):
        allowed_type = [".pdf", ".docs", ".docx"]

        file_extension = os.path.splitext(resume_file.name)[1].lower()

        if file_extension not in allowed_type:
            raise ValueError(f"Invalid file type:{file_extension}")

        current_value = getattr(self, "resume", None)
        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, presigned_url = upload_file_to_bucket(
                resume_file,
                allowed_type,
                "JobResume/",
                str(self.id),
                None,
            )
            self.resume = aws_file_url
            self.save(update_fields=["resume"])
            return aws_file_url
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload resume: {str(e)}")
