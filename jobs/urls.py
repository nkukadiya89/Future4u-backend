"""
URL configuration for the jobs app.

Endpoints:
  GET /api/jobs/search/      – search real jobs by keyword/location/filters
  GET /api/jobs/recommended/ – load AI recommendation → matching LinkedIn jobs
"""

from django.urls import path

from jobs.views import JobSearchAPIView, RecommendedJobsAPIView

urlpatterns = [
    path(
        "api/jobs/search/",
        JobSearchAPIView.as_view(),
        name="job-search",
    ),
    path(
        "api/jobs/recommended/",
        RecommendedJobsAPIView.as_view(),
        name="job-recommended",
    ),
]
