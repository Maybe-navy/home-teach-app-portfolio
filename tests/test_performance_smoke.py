from django.urls import reverse
from django.contrib.auth.models import User
from personal_info.models import TeacherProfile, StudentProfile, TeacherStudentAssignment
from core.models import UserProfile
import pytest


def make_admin():
    u = User.objects.create_user("admin2", password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": "admin",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return u


def make_teacher(i):
    u = User.objects.create_user(f"t{i}", password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": "teacher",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return TeacherProfile.objects.create(user=u, name=f"T{i}", gender="man", age=30, address="a", phone="1", email=f"t{i}@ex.com", grade="college_1")


def make_student(i):
    u = User.objects.create_user(f"s{i}", password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": "student",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return StudentProfile.objects.create(user=u, name=f"S{i}", gender="man", age=15, address="a", phone="1", email=f"s{i}@ex.com", school="", grade="junior_1")


@pytest.mark.django_db
def test_assignment_list_queries(client, django_assert_num_queries):
    admin = make_admin()
    teacher = make_teacher(1)
    student = make_student(1)
    TeacherStudentAssignment.objects.create(teacher=teacher, student=student)
    client.force_login(admin)
    url = reverse("admin_portal:assignment_list")
    with django_assert_num_queries(14):
        client.get(url)
