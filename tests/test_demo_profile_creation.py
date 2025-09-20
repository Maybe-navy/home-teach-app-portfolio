import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse

from core.models import UserProfile
from personal_info.models import TeacherProfile, StudentProfile


@pytest.mark.django_db
def test_demo_teacher_profile_auto_created(client, settings):
    settings.DEMO_READ_ONLY = True
    user = User.objects.create_user(username="T100000", password="demo-pass")
    UserProfile.objects.filter(user=user).update(
        user_type="teacher",
        is_locked=False,
        failed_login_attempts=0,
        is_temporary_password=False,
    )

    resp = client.post(reverse("core:login"), {"username": "T100000", "password": "demo-pass"})
    assert resp.status_code == 302
    assert TeacherProfile.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_demo_student_profile_auto_created(client, settings, monkeypatch):
    settings.DEMO_READ_ONLY = True
    user = User.objects.create_user(username="S100000", password="demo-pass")
    UserProfile.objects.filter(user=user).update(
        user_type="student",
        is_locked=False,
        failed_login_attempts=0,
        is_temporary_password=False,
    )

    monkeypatch.setattr("core.views.redirect", lambda to, *args, **kwargs: HttpResponse("ok"))

    resp = client.post(reverse("core:login"), {"username": "S100000", "password": "demo-pass"})
    assert resp.status_code == 200
    assert StudentProfile.objects.filter(user=user).exists()
