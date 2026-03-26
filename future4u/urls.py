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
from django.urls import path
from user.user_auth import CustomTokenObtainPairView
from django.urls import include
from future4u.routers import future4u_router

urlpatterns = [
    path('admin/', admin.site.urls),
    path("get-token/", CustomTokenObtainPairView.as_view(), name="get_token"),
    path("", include(future4u_router.urls)),
    path("", include("subscription.urls")),
]
