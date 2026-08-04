from django.urls import path
from rest_framework.routers import DefaultRouter

from .jobs_views import (
    JobApplicationNoteViewSet,
    JobApplicationViewSet,
    JobViewSet,
)
from .views import (
    InternshipApplicationNoteViewSet,
    InternshipApplicationViewSet,
    InternshipViewSet,
)

internship_job_router = DefaultRouter()

internship_job_router.register(
    r"internship", InternshipViewSet, basename="internship_router"
)
internship_job_router.register(
    r"internship_application",
    InternshipApplicationViewSet,
    basename="internship_application_router",
)
internship_job_router.register(r"job", JobViewSet, basename="job_router")
internship_job_router.register(
    r"job_application", JobApplicationViewSet, basename="job_application_router"
)

internship_application_note_urls = [
    path(
        "internship-applications/<int:application_id>/notes/",
        InternshipApplicationNoteViewSet.as_view({"get": "list", "post": "create"}),
        name="internship-application-notes-list",
    ),
    path(
        "internship-applications/<int:application_id>/notes/<int:pk>/",
        InternshipApplicationNoteViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="internship-application-notes-detail",
    ),
]

job_application_note_urls = [
    path(
        "job-applications/<int:application_id>/notes/",
        JobApplicationNoteViewSet.as_view({"get": "list", "post": "create"}),
        name="job-application-notes-list",
    ),
    path(
        "job-applications/<int:application_id>/notes/<int:pk>/",
        JobApplicationNoteViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="job-application-notes-detail",
    ),
]
