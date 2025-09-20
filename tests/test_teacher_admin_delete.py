import pytest
from datetime import date, time
from django.urls import reverse
from django.contrib.auth.models import User

from core.models import UserProfile
from personal_info.models import (
    TeacherProfile,
    StudentProfile,
    Subject,
    TeacherStudentAssignment,
    ClassSchedule,
)


def create_admin_user(username="admin"):
    user = User.objects.create_user(username=username, password="pw")
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


def create_teacher(username="teacher"):
    user = User.objects.create_user(username=username, password="pw")
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "user_type": "teacher",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return TeacherProfile.objects.create(
        user=user,
        name=username,
        gender="man",
        age=30,
        address="addr",
        phone="000",
        email=f"{username}@ex.com",
        grade="college_1",
    )


def create_student(username="student"):
    user = User.objects.create_user(username=username, password="pw")
    UserProfile.objects.update_or_create(
        user=user,
        defaults={
            "user_type": "student",
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return StudentProfile.objects.create(
        user=user,
        name=username,
        gender="man",
        age=15,
        address="addr",
        phone="000",
        email=f"{username}@ex.com",
        school="",
        grade="junior_1",
    )


@pytest.mark.django_db
def test_admin_can_delete_teacher(client):
    admin_user = create_admin_user()
    teacher = create_teacher("teacher_a")
    student = create_student("student_a")
    subject = Subject.objects.create(name="Math")
    TeacherStudentAssignment.objects.create(teacher=teacher, student=student)
    ClassSchedule.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )

    client.force_login(admin_user)
    url = reverse("admin_portal:teacher_delete", kwargs={"pk": teacher.pk})

    resp_get = client.get(url)
    assert resp_get.status_code == 200
    assert resp_get.context["assignment_count"] == 1
    assert resp_get.context["schedule_count"] == 1

    teacher_id = teacher.pk
    teacher_user_id = teacher.user_id

    resp_post = client.post(url)
    assert resp_post.status_code == 302
    assert not TeacherProfile.objects.filter(pk=teacher_id).exists()
    assert not User.objects.filter(pk=teacher_user_id).exists()
    assert TeacherStudentAssignment.objects.count() == 0

    schedule = ClassSchedule.objects.get(student=student)
    assert schedule.teacher_id is None


@pytest.mark.django_db
def test_non_admin_cannot_delete_teacher(client):
    target_teacher = create_teacher("target")
    other_teacher = create_teacher("other")

    client.force_login(other_teacher.user)
    url = reverse("admin_portal:teacher_delete", kwargs={"pk": target_teacher.pk})

    resp = client.post(url)
    assert TeacherProfile.objects.filter(pk=target_teacher.pk).exists()
    assert resp.status_code in (302, 403)


@pytest.mark.django_db
def test_admin_can_delete_student(client):
    admin_user = create_admin_user("admin_student")
    teacher = create_teacher("teacher_for_student")
    student = create_student("student_target")
    subject = Subject.objects.create(name="Science")
    TeacherStudentAssignment.objects.create(teacher=teacher, student=student)
    ClassSchedule.objects.create(
        teacher=teacher,
        student=student,
        subject=subject,
        class_date=date(2024, 2, 1),
        start_time=time(12, 0),
        end_time=time(13, 0),
    )

    client.force_login(admin_user)
    url = reverse("admin_portal:student_delete", kwargs={"pk": student.pk})

    resp_get = client.get(url)
    assert resp_get.status_code == 200
    assert resp_get.context["assignment_count"] == 1
    assert resp_get.context["schedule_count"] == 1

    student_id = student.pk
    student_user_id = student.user_id

    resp_post = client.post(url)
    assert resp_post.status_code == 302
    assert not StudentProfile.objects.filter(pk=student_id).exists()
    assert not User.objects.filter(pk=student_user_id).exists()
    assert TeacherStudentAssignment.objects.count() == 0
    assert not ClassSchedule.objects.filter(student_id=student_id).exists()


@pytest.mark.django_db
def test_teacher_delete_allows_admin_in_demo_mode(client, monkeypatch):
    admin_user = create_admin_user("demo_admin")
    teacher = create_teacher("demo_teacher")

    monkeypatch.setattr("admin_portal.views._demo_lockdown_active", lambda: True)

    client.force_login(admin_user)
    url = reverse("admin_portal:teacher_delete", kwargs={"pk": teacher.pk})

    resp_get = client.get(url)
    assert resp_get.status_code == 200

    resp_post = client.post(url)
    assert resp_post.status_code == 302


@pytest.mark.django_db
def test_student_delete_allows_admin_in_demo_mode(client, monkeypatch):
    admin_user = create_admin_user("demo_admin_student")
    student = create_student("demo_student")

    monkeypatch.setattr("admin_portal.views._demo_lockdown_active", lambda: True)

    client.force_login(admin_user)
    url = reverse("admin_portal:student_delete", kwargs={"pk": student.pk})

    resp_get = client.get(url)
    assert resp_get.status_code == 200

    resp_post = client.post(url)
    assert resp_post.status_code == 302
