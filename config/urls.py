"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
import os
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from core import views as core_views

ADMIN_URL = os.getenv("ADMIN_URL", "admin-8c1b3f1c/")

urlpatterns = [
    path('', core_views.home_redirect, name='home'),
    path(ADMIN_URL, admin.site.urls),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('auth/', include('core.urls'), name='core'),  # ログイン
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='core:login'), name='logout'),
    path(
        'portal/admin/',
        include(('admin_portal.urls', 'admin_portal'), namespace='admin_portal'),
    ),  # 管理者
    path(
        'portal/teacher/',
        include(('teacher_portal.urls', 'teacher_portal'), namespace='teacher_portal'),
    ),  # 講師
    path(
        'portal/student/',
        include(('student_portal.urls', 'student_portal'), namespace='student_portal'),
    ),
    path(
        'portal/personal/',
        include(('personal_info.urls', 'personal_info'), namespace='personal_info'),
    ),
    path("health/live", core_views.health_live, name="health_live"),
    path("health/ready", core_views.health_ready, name="health_ready"),
    path("metrics", core_views.metrics, name="metrics"),
]

handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
