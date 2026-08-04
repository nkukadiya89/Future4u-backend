from django.contrib import admin

from .models import (
    Internship,
    InternshipApplication,
    InternshipApplicationNote,
    Job,
    JobApplication,
    JobApplicationNote,
)

# Register your models here.
admin.site.register(Internship)
admin.site.register(InternshipApplication)
admin.site.register(InternshipApplicationNote)
admin.site.register(Job)
admin.site.register(JobApplication)
admin.site.register(JobApplicationNote)
