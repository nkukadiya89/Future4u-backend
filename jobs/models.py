from django.conf import settings
from django.db import models
from django.utils.timezone import now


# Create your models here.
class Job(models.Model):
    title = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)

    description = models.TextField()

    domain = models.ForeignKey("domain.Domain", on_delete=models.SET_NULL, null=True)

    employment_type = models.CharField(
        max_length=50,
        choices=(
            ("full_time", "Full Time"),
            ("part_time", "Part Time"),
            ("contract", "Contract"),
            ("internship", "Internship"),
        ),
    )

    experience_min = models.IntegerField(null=True, blank=True)
    experience_max = models.IntegerField(null=True, blank=True)

    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)

    location = models.CharField(max_length=150, null=True, blank=True)

    work_mode = models.CharField(
        max_length=50,
        choices=(
            ("remote", "Remote"),
            ("onsite", "Onsite"),
            ("hybrid", "Hybrid"),
        ),
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="job_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Job<{self.id} - {self.title}>"  # type: ignore

    class Meta:
        db_table = "job"
        ordering = ["-created_at"]


"""
Defines skill requirements for a job with depth (not just presence).

Captures:
- required skill
- expected proficiency level
- whether it is mandatory or optional

WHY IT MATTERS:
Basic matching ("user has React") is useless.
We need level-based and priority-based matching.

Example:
Job requires:
- React (advanced, mandatory)
- Redux (intermediate, optional)

User:
- React (beginner) → weak match
- React (advanced) → strong match

Used in scoring:
- mandatory skills → higher weight
- level mismatch → penalty
"""


class JobSkill(models.Model):
    LEVEL_CHOICES = (
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    )

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="skill_requirements"
    )
    skill = models.ForeignKey("skill.Skill", on_delete=models.CASCADE)

    required_level = models.CharField(max_length=20, choices=LEVEL_CHOICES)

    is_mandatory = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="jobskill_updated",
    )
    updated_at = models.DateTimeField(default=now)
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobskill_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"JobSkill<{self.id} - {self.skill.name}>"  # type: ignore

    class Meta:
        db_table = "job_skill"
        ordering = ["-created_at"]


"""
Defines hidden expectations of a job beyond hard requirements.

Captures:
- soft skills
- industry preferences
- education requirements
- constraints like notice period

WHY IT MATTERS:
Two candidates with same skills are not equal.
Fit depends on behavioral and contextual alignment.

Example:
Job prefers:
- fast-paced startup mindset
- notice period < 30 days

User:
- prefers stable corporate → mismatch
- 90-day notice → low priority

Used in recommendation:
→ filters or downgrades candidates even if skills match
"""


class JobPreference(models.Model):
    job = models.OneToOneField(
        Job, on_delete=models.CASCADE, related_name="preferences"
    )

    preferred_industries = models.JSONField(default=list, blank=True)

    soft_skills = models.ManyToManyField("skill.Skill", blank=True)

    education_requirement = models.CharField(max_length=150, null=True, blank=True)

    notice_period_days = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="jobpreference_updated",
    )
    updated_at = models.DateTimeField(default=now)
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobpreference_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"JobPreference<{self.id} - {self.job.title}>"  # type: ignore

    class Meta:
        db_table = "job_preference"
        ordering = ["-created_at"]


"""
Tracks user interaction with jobs and outcome.

Acts as feedback loop for recommendation engine.

WHY IT MATTERS:
Without this, system cannot learn from:
- user interest (applied)
- company response (shortlisted/rejected)

Example:
User applied to:
- 5 frontend jobs
- rejected in all due to low React level

System learns:
→ stop recommending advanced roles
→ suggest upskilling instead

Also used for:
- personalization
- ranking future recommendations
"""


class JobApplication(models.Model):
    STATUS_CHOICES = (
        ("applied", "Applied"),
        ("shortlisted", "Shortlisted"),
        ("rejected", "Rejected"),
        ("hired", "Hired"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey("user_profile.Profile", on_delete=models.CASCADE)

    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    cover_letter = models.TextField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")

    applied_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="jobapplication_updated",
    )
    updated_at = models.DateTimeField(default=now)
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobapplication_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"JobApplication<{self.id} - {self.job.title}>"  # type: ignore

    class Meta:
        db_table = "job_application"
        ordering = ["-created_at"]


"""
Captures implicit user interest (without applying).

Represents intent signal stronger than browsing.

WHY IT MATTERS:
Not all users apply immediately.
Saved jobs indicate preference direction.

Example:
User saves:
- multiple Data Science jobs

System infers:
→ user is exploring transition to Data Science
→ recommend relevant courses + beginner roles

Used for:
- early-stage recommendation tuning
- interest prediction before action
"""


class SavedJob(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    saved_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="savedjob_updated",
    )
    updated_at = models.DateTimeField(default=now)
    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="savedjob_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"SavedJob<{self.id} - {self.job.title}>"  # type: ignore

    class Meta:
        db_table = "saved_job"
        ordering = ["-created_at"]
