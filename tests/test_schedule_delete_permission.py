import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, time

from core.models import UserProfile
from personal_info.models import TeacherProfile, StudentProfile, Subject, ClassSchedule


def create_admin_user():
    user = User.objects.create_user(username="admin", password="pw")
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "user_type": "admin",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return user


def create_teacher(name="T1"):
    u = User.objects.create_user(username=name, password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": "teacher",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return TeacherProfile.objects.create(
        user=u,
        name=name,
        gender="man",
        age=30,
        address="a",
        phone="1",
        email=f"{name}@ex.com",
        grade="college_1",
    )


def create_student(name="S1"):
    u = User.objects.create_user(username=name, password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": "student",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return StudentProfile.objects.create(
        user=u,
        name=name,
        gender="man",
        age=15,
        address="a",
        phone="1",
        email=f"{name}@ex.com",
        school="",
        grade="junior_1",
    )


@pytest.mark.django_db
def test_teacher_cannot_delete_schedule(client):
    teacher = create_teacher()
    student = create_student()
    subject = Subject.objects.create(name="Math")
    schedule = ClassSchedule.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )

    client.force_login(teacher.user)
    url = reverse("admin_portal:delete_schedule", kwargs={"schedule_id": schedule.id})
    resp = client.post(url)
    assert resp.status_code == 403
    assert ClassSchedule.objects.filter(id=schedule.id).exists()


@pytest.mark.django_db
def test_admin_can_delete_schedule(client):
    admin = create_admin_user()
    teacher = create_teacher("T2")
    student = create_student("S2")
    subject = Subject.objects.create(name="Science")
    schedule = ClassSchedule.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )

    client.force_login(admin)
    url = reverse("admin_portal:delete_schedule", kwargs={"schedule_id": schedule.id})
    resp = client.post(url)
    assert resp.status_code == 302
    assert not ClassSchedule.objects.filter(id=schedule.id).exists()
