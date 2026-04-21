from django.conf import settings
from django.db import models
from django.utils.timezone import now


# Create your models here.
class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()

    provider_name = models.CharField(max_length=200)

    domains = models.ManyToManyField("Domain", blank=True)
    skills = models.ManyToManyField("Skill", blank=True)

    level = models.CharField(
        max_length=50,
        choices=(
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ),
    )

    duration_hours = models.IntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_certified = models.BooleanField(default=False)
    certification_name = models.CharField(max_length=200, null=True, blank=True)

    course_link = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="course_updated",
    )
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Course<{self.id} - {self.title}>"  # type: ignore

    class Meta:
        db_table = "course"
        ordering = ["-created_at"]


class CourseEnrollment(models.Model):
    STATUS_CHOICES = (
        ("enrolled", "Enrolled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("dropped", "Dropped"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Optional: tie to specific profile (important for your multi-profile system)
    profile = models.ForeignKey(
        "Profile", on_delete=models.CASCADE, null=True, blank=True
    )

    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")

    progress_percentage = models.IntegerField(default=0)

    # WHY user took this (critical for recommendation engine later)
    purpose = models.CharField(max_length=200, null=True, blank=True)

    # who initiated → parent / self / corporate
    initiated_by = models.CharField(
        max_length=50,
        choices=(
            ("self", "Self"),
            ("parent", "Parent"),
            ("corporate", "Corporate"),
        ),
        default="self",
    )
    created_at = models.DateTimeField(default=now)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="course_enrollment_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_enrollment_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CourseEnrollment<{self.id} - {self.course.title} - {self.user.username}>"  # type: ignore

    class Meta:
        db_table = "course_enrollment"
        ordering = ["-enrolled_at"]


"""
WHY THIS MODEL EXISTS:

Enrollment only tells us that a user signed up or completed a course.
It does NOT tell us whether the course had any real impact.

CourseOutcome captures the RESULT of learning:
- What skills were actually gained (not just taught)
- Whether the course improved employability
- Proof like certificates
- User-perceived effectiveness (completion_rating)

WHY IT MATTERS FOR RECOMMENDATION:

Without this:
- We recommend courses blindly based on metadata (domain/skill tags)
- We cannot measure effectiveness of courses
- We cannot prioritize courses that actually improve outcomes

With this:
- We can recommend courses that led to real skill gains for similar users
- We can rank courses based on outcome success rate
- We can update user's profile strength dynamically after completion

Example:
"Users like you who completed Course X improved React skill → recommend Course X"
"""


class CourseOutcome(models.Model):
    enrollment = models.OneToOneField(CourseEnrollment, on_delete=models.CASCADE)

    skills_gained = models.ManyToManyField("Skill", blank=True)

    completion_rating = models.IntegerField(null=True, blank=True)  # 1–5

    certificate_url = models.URLField(null=True, blank=True)

    # measurable impact
    outcome_summary = models.TextField(null=True, blank=True)

    # optional: used in matching later
    improved_employability = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="course_outcome_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_outcome_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CourseOutcome<{self.id} - {self.enrollment.course.title} - {self.enrollment.user.username}>"  # type: ignore

    class Meta:
        db_table = "course_outcome"
        ordering = ["-created_at"]


"""
WHY THIS MODEL EXISTS:

CourseOutcome measures effectiveness.
CourseReview measures user sentiment.

These are NOT the same thing.

A course can:
- Have high ratings (easy, engaging)
- But low impact (no real skill gain)

Or:
- Be difficult (lower rating)
- But high impact (strong career benefit)

WHY IT MATTERS FOR RECOMMENDATION:

Without separating review from outcome:
- We risk recommending "popular but useless" courses

With this separation:
- We can balance:
    - Quality (reviews)
    - Effectiveness (outcomes)

Example:
- Course A: 4.8 rating but low skill gain → avoid over-recommending
- Course B: 3.8 rating but high employability impact → prioritize

This enables smarter ranking instead of naive "top-rated courses".
"""


class CourseReview(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    rating = models.IntegerField()  # 1–5
    review = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="course_review_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_review_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"CourseReview<{self.id} - {self.course.title} - {self.user.username}>"  # type: ignore

    class Meta:
        db_table = "course_review"
        ordering = ["-created_at"]


"""
WHY THIS MODEL EXISTS:

User profile tells us:
- current state (skills, background)

But it does NOT clearly define:
- future intent
- learning direction

ProfileCoursePreference captures:
- What domains the user wants to move into
- What skills they want to build
- Their goal (career switch, promotion, etc.)

WHY IT MATTERS FOR RECOMMENDATION:

Without this:
- Recommendations are reactive (based only on past data)
- We assume user's future = past (which is wrong)

With this:
- Recommendations become proactive and goal-driven

Example:
User:
- Current: Mechanical Engineer
- Preference: Data Science

System can:
→ Recommend Python, ML courses
→ Not mechanical courses (even if past data suggests it)

This is critical for:
- career transitions
- upskilling journeys
- personalized learning paths
"""


class ProfileCoursePreference(models.Model):
    profile = models.ForeignKey("Profile", on_delete=models.CASCADE)

    preferred_domains = models.ManyToManyField("Domain", blank=True)
    preferred_skills = models.ManyToManyField("Skill", blank=True)

    goal = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="profile_course_preference_updated",
    )
    updated_at = models.DateTimeField(default=now)

    deleted = models.BooleanField(default=False)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile_course_preference_deleted",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ProfileCoursePreference<{self.id} - {self.profile.user.username}>"  # type: ignore

    class Meta:
        db_table = "profile_course_preference"
        ordering = ["-created_at"]
