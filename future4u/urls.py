from django.contrib import admin
from django.urls import include
from django.urls import path

from future4u.routers import future4u_router
from recommendation.views import CareerDetailsAPIView, RecommendationDomainDetailAPIView, RecommendationListAPIView
from user.user_auth import CustomTokenObtainPairView
from user_profile.views import UserProfileViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path("get-token/", CustomTokenObtainPairView.as_view(), name="get_token"),
    path(
        "api/profile/",
        UserProfileViewSet.as_view({"get": "list", "post": "create", "patch": "partial_update"}),
        name="api-profile",
    ),
    path("api/recommendations/", RecommendationListAPIView.as_view(), name="api-recommendations"),
    path(
        "api/recommendations/domain/<uuid:id>/",
        RecommendationDomainDetailAPIView.as_view(),
        name="api-recommendations-domain-detail",
    ),
    path("api/careers/<uuid:id>/details/", CareerDetailsAPIView.as_view(), name="api-career-details"),
    path("", include(future4u_router.urls)),
    path("", include("subscription.urls")),
]
