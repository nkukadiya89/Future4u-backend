from django.contrib import admin
from .models import Internship, Job, InternshipApplication

# Register your models here.
admin.site.register(Internship)
admin.site.register(InternshipApplication)
admin.site.register(Job)
