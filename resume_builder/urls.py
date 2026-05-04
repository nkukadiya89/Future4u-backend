from django.urls import path
from resume_builder.views import ResumeGenerateView, ResumePreviewView

urlpatterns = [
    path("api/resume/generate/", ResumeGenerateView.as_view(), name="resume-generate"),
    path("api/resume/preview/", ResumePreviewView.as_view(), name="resume-preview"),
]
