from django.db import models
from common.models import BaseModule
from django.conf import settings
from city.models import City
# Create your models here.

class Courses(BaseModule):
    
    COURSE_TYPE_CHOICES = (
        ("higher_secondary", "Higher Secondary"),
        ("diploma", "Diploma"),
        ("degree", "Degree"),
        ("certification", "Certification"),
        ("training", "Training"),
    )

    MODE_CHOICE = (
        ("online", "Online"),
        ("offline", "Offline"),
    )

    name = models.CharField(max_length=200)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICE)
    skills = models.JSONField(default=list, blank=True)
    education_tags = models.JSONField(default=list, blank=True)
    duration = models.CharField(max_length=100, null=True, blank=True)
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,null=True, blank=True, related_name="courses")
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    course_overview = models.TextField(null=True, blank=True)
    why_this_course = models.JSONField(default=list, blank=True)
    certification_info = models.TextField(null=True, blank=True)
    course_content = models.JSONField(default=list, blank=True)
    class Meta:
        db_table = "courses"
        ordering = ["-created_at"]
    def __str__(self):
        return self.name
    
class CourseInquiry(BaseModule):

    INQUIRIES_STATUS_CHOICE = (
        ("pending","Pending"),
        ("responded","Responded"),
        ("closed","Closed"),
    )
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, related_name="inquiries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="course_inquiries")
    name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=INQUIRIES_STATUS_CHOICE, default="pending", null=True, blank=True)
    class Meta:
        db_table = "course_inquiry"

    def __str__(self):
        return f"{self.course.name} - {self.email}"
