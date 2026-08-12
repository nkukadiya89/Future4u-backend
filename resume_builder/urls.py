from django.urls import path

from resume_builder.views import (
    ResumeDetailView,
    ResumeGenerateView,
    ResumeHistoryView,
    ResumePDFView,
    ResumePreviewView,
    ResumeTemplatesView,
)

urlpatterns = [
    path("api/resume/templates/", ResumeTemplatesView.as_view(), name="resume-templates"),
    path("api/resume/generate/", ResumeGenerateView.as_view(), name="resume-generate"),
    path("api/resume/preview/", ResumePreviewView.as_view(), name="resume-preview"),
    path("api/resume/", ResumeHistoryView.as_view(), name="resume-history"),
    path(
        "api/resume/<int:resume_id>/pdf/",
        ResumePDFView.as_view(),
        name="resume-pdf",
    ),
    path(
        "api/resume/<int:resume_id>/",
        ResumeDetailView.as_view(),
        name="resume-detail",
    ),
]
