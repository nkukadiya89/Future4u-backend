"""
URL configuration for future4u project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from user.user_auth import CustomTokenObtainPairView
from future4u.routers import future4u_router
from assessment_career.course_views import AIRecommendationCoursesAPIView
from services.ai.views import AIRecommendationAPIView
from recommendation.views import (
    CareerDetailsAPIView,
    RecommendationDomainDetailAPIView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("get-token/", CustomTokenObtainPairView.as_view(), name="get_token"),
    path(
        "api/ai-recommendations/<int:assessment_id>/",
        AIRecommendationAPIView.as_view(),
        name="api-ai-recommendations",
    ),
    path(
        "api/ai-recommendations/<int:assessment_id>/courses/",
        AIRecommendationCoursesAPIView.as_view(),
        name="api-ai-recommendations-courses",
    ),
    path(
        "api/recommendations/domain/<uuid:id>/",
        RecommendationDomainDetailAPIView.as_view(),
        name="api-recommendations-domain-detail",
    ),
    path(
        "api/careers/<uuid:id>/details/",
        CareerDetailsAPIView.as_view(),
        name="api-career-details",
    ),
    path("", include(future4u_router.urls)),
    path("", include("subscription.urls")),
    path("api/v1/", include("subscription.urls")),
    path("", include("resume_builder.urls")),
]
