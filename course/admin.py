from django.contrib import admin

from .models import CourseInquiry, Courses

# Register your models here.
admin.site.register(Courses)
admin.site.register(CourseInquiry)
