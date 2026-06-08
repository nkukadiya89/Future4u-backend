from django.db import models
from common.models import BaseModule
from city.models import City
from django.conf import settings
from education_level.models import EducationLevel

# Create your models here.
class Internship(BaseModule):
    
    INTERNSHIP_TYPE_CHOICES = (
        ("free","Free"),
        ("paid","Paid"),
        ("stipend","Stipend"),
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
    internship_type = models.CharField(max_length=150, choices=INTERNSHIP_TYPE_CHOICES, default="free")
    mode = models.CharField(max_length=150, choices=MODE_CHOICE, default="offline")
    duration = models.CharField(max_length=150, null=True, blank=True)
    fees_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stipend_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    certificate_provided = models.BooleanField(default=True)
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="internships")

    class Meta:
        db_table = "internship"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name