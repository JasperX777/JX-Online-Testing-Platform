"""
URL configuration for config project.

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
from django.urls import include, path
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import MeView, RegisterView


class PingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "pong", "user": request.user.username})


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "OK"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('projects.urls')),
    path('api/', include('testcases.urls')),
    path('api/', include('executions.urls')),

    # Public
    path('api/health/', HealthView.as_view(), name='health'),
    path('api/auth/register/', RegisterView.as_view(), name='auth_register'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Protected
    path('api/ping/', PingView.as_view(), name='ping'),
    path('api/auth/me/', MeView.as_view(), name='auth_me'),
]
