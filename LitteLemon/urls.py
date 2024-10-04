"""
URL configuration for LitteLemon project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from djoser.views import TokenCreateView #, UserViewSet
from rest_framework.routers import DefaultRouter

# Create a router and register the UserViewSet with the custom path
# router = DefaultRouter()
# router.register(r'', UserViewSet, basename='user')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('LittleLemonAPI.urls')),
    # path('api/users/', include(router.urls)), # Custom path for user viewset
    path('token/login/', TokenCreateView.as_view(), name='token-login'), # Custom path for token login
    path('auth/token/login/', TokenCreateView.as_view(), name='auth-token-login'), 
    path('api/users/', include('djoser.urls')),
    path('api/users/', include('djoser.urls.authtoken')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
