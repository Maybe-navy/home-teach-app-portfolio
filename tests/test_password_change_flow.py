import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from core.models import UserProfile
from personal_info.models import TeacherProfile, StudentProfile


def _create_teacher_user(username="T500000"):
    user = User.objects.create_user(username=username, password="TempPass1!")
    profile = user.userprofile
    profile.user_type = "teacher"
    profile.is_temporary_password = True
    profile.is_locked = False
    profile.failed_login_attempts = 0
    profile.save(update_fields=["user_type", "is_temporary_password", "is_locked", "failed_login_attempts"])
    TeacherProfile.objects.get_or_create(
        user=user,
        defaults={
            "name": username,
            "gender": "man",
            "age": 25,
            "address": "demo",
            "phone": "000-0000-0000",
            "email": f"{username}@example.com",
            "school": "demo",
            "grade": "college_1",
        },
    )
    return user


def _create_student_user(username="S500000"):
    user = User.objects.create_user(username=username, password="TempPass1!")
    profile = user.userprofile
    profile.user_type = "student"
    profile.is_temporary_password = True
    profile.is_locked = False
    profile.failed_login_attempts = 0
    profile.save(update_fields=["user_type", "is_temporary_password", "is_locked", "failed_login_attempts"])
    StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            "name": username,
            "gender": "man",
            "age": 15,
            "address": "demo",
            "phone": "000-0000-0000",
            "email": f"{username}@example.com",
            "school": "demo",
            "grade": "junior_1",
        },
    )
    return user


@pytest.mark.django_db
def test_teacher_password_change_in_demo(client, settings):
    settings.DEMO_READ_ONLY = True
    user = _create_teacher_user()

    login_resp = client.post(
        reverse("core:login"), {"username": user.username, "password": "TempPass1!"}, follow=True
    )
    assert login_resp.status_code == 200
    assert login_resp.resolver_match.view_name == "core:change_password"

    new_pw = "SecurePass1!"
    resp = client.post(reverse("core:change_password"), {"new_password": new_pw, "confirm_password": new_pw})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(reverse("teacher_portal:teacher_dashboard"))

    profile = UserProfile.objects.get(user=user)
    assert profile.is_temporary_password is False


@pytest.mark.django_db
def test_student_password_change_in_demo(client, settings):
    settings.DEMO_READ_ONLY = True
    user = _create_student_user()

    login_resp = client.post(
        reverse("core:login"), {"username": user.username, "password": "TempPass1!"}, follow=True
    )
    assert login_resp.status_code == 200
    assert login_resp.resolver_match.view_name == "core:change_password"

    new_pw = "SecurePass1!"
    resp = client.post(reverse("core:change_password"), {"new_password": new_pw, "confirm_password": new_pw})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(reverse("student_portal:my_schedule_list"))

    profile = UserProfile.objects.get(user=user)
    assert profile.is_temporary_password is False


@pytest.mark.django_db
def test_admin_login_path(client):
    user = User.objects.create_user(username="A500000", password="AdminPass1!")
    profile = user.userprofile
    profile.user_type = "admin"
    profile.is_locked = False
    profile.save(update_fields=["user_type", "is_locked"])

    resp = client.post(reverse("core:login"), {"username": user.username, "password": "AdminPass1!"})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(reverse("admin_portal:admin_dashboard"))
