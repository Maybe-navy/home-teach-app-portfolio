import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, time

from core.models import UserProfile
from personal_info.models import (
    TeacherProfile,
    StudentProfile,
    Subject,
    ClassSchedule,
    TeacherStudentAssignment,
)


@pytest.fixture
def subject(db):
    return Subject.objects.create(name="Math")


@pytest.fixture
def teacher_user(db):
    user = User.objects.create_user(username="teacher", password="pw")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.user_type = "teacher"
    profile.is_temporary_password = False
    profile.failed_login_attempts = 0
    profile.is_locked = False
    profile.save(update_fields=[
        "user_type",
        "is_temporary_password",
        "failed_login_attempts",
        "is_locked",
    ])
    return user


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(username="student", password="pw")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.user_type = "student"
    profile.is_temporary_password = False
    profile.failed_login_attempts = 0
    profile.is_locked = False
    profile.save(update_fields=[
        "user_type",
        "is_temporary_password",
        "failed_login_attempts",
        "is_locked",
    ])
    return user


@pytest.fixture
def teacher_profile(teacher_user):
    return TeacherProfile.objects.create(
        user=teacher_user,
        name="T",
        gender="man",
        age=30,
        address="a",
        phone="1",
        email="t@example.com",
        grade="college_1",
    )


@pytest.fixture
def student_profile(student_user):
    return StudentProfile.objects.create(
        user=student_user,
        name="S",
        gender="man",
        age=15,
        address="a",
        phone="1",
        email="s@example.com",
        school="",
        grade="junior_1",
    )


@pytest.fixture
def seed_schedules(teacher_profile, student_profile, subject):
    schedule = ClassSchedule.objects.create(
        teacher=teacher_profile,
        student=student_profile,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    return [schedule]


@pytest.fixture
def another_teacher_user(db):
    user = User.objects.create_user(username="teacher2", password="pw")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.user_type = "teacher"
    profile.is_temporary_password = False
    profile.failed_login_attempts = 0
    profile.is_locked = False
    profile.save(update_fields=[
        "user_type",
        "is_temporary_password",
        "failed_login_attempts",
        "is_locked",
    ])
    return user


@pytest.fixture
def another_teacher_profile(another_teacher_user):
    return TeacherProfile.objects.create(
        user=another_teacher_user,
        name="T2",
        gender="man",
        age=30,
        address="a",
        phone="1",
        email="t2@example.com",
        grade="college_1",
    )


@pytest.mark.django_db
def test_csv_permission_forbidden(client, student_user, student_profile, seed_schedules):
    url = reverse("teacher_portal:student_schedule_csv", kwargs={"student_id": student_profile.id})
    client.force_login(student_user)
    resp = client.get(url)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_pdf_permission_forbidden(client, student_user, student_profile, seed_schedules):
    url = reverse("teacher_portal:student_schedule_pdf", kwargs={"student_id": student_profile.id})
    client.force_login(student_user)
    resp = client.get(url)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_csv_download_ok(client, teacher_user, teacher_profile, student_profile, seed_schedules):
    url = reverse("teacher_portal:student_schedule_csv", kwargs={"student_id": student_profile.id})
    client.force_login(teacher_user)
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    lines = resp.content.decode("utf-8-sig").splitlines()
    assert lines[0] == "予定日,開始,終了,講師名,科目名"


@pytest.mark.django_db
def test_pdf_download_ok(client, teacher_user, student_profile, seed_schedules):
    url = reverse("teacher_portal:student_schedule_pdf", kwargs={"student_id": student_profile.id})
    client.force_login(teacher_user)
    resp = client.get(url)
    assert resp.status_code == 200
    assert "attachment" in resp["Content-Disposition"].lower()


@pytest.mark.django_db
def test_conflict_detection_on_update(client, teacher_user, teacher_profile, student_profile, subject):
    schedule1 = ClassSchedule.objects.create(
        teacher=teacher_profile,
        student=student_profile,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    schedule2 = ClassSchedule.objects.create(
        teacher=teacher_profile,
        student=student_profile,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(11, 0),
        end_time=time(12, 0),
    )
    url = reverse("teacher_portal:teacher_edit_schedule", kwargs={"schedule_id": schedule1.id})
    client.force_login(teacher_user)
    resp = client.post(
        url,
        {
            "class_date": "2024-01-01",
            "start_time": "11:30",
            "end_time": "12:30",
            "notes": "",
        },
    )
    assert resp.status_code == 400
    assert "重複" in resp.content.decode()


@pytest.mark.django_db
def test_assigned_teacher_can_edit_unassigned_schedule(
    client,
    teacher_user,
    teacher_profile,
    student_profile,
    subject,
    another_teacher_profile,
):
    schedule = ClassSchedule.objects.create(
        teacher=another_teacher_profile,
        student=student_profile,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    TeacherStudentAssignment.objects.create(
        teacher=teacher_profile, student=student_profile
    )

    client.force_login(teacher_user)
    url = reverse("teacher_portal:teacher_edit_schedule", kwargs={"schedule_id": schedule.id})
    resp = client.post(
        url,
        {
            "teacher": teacher_profile.id,
            "class_date": "2024-01-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "notes": "updated",
        },
    )
    assert resp.status_code == 302
    schedule.refresh_from_db()
    assert schedule.teacher_id == teacher_profile.id
    assert schedule.notes == "updated"


@pytest.mark.django_db
def test_unassigned_teacher_cannot_edit_schedule(
    client,
    teacher_user,
    teacher_profile,
    student_profile,
    subject,
    another_teacher_profile,
):
    schedule = ClassSchedule.objects.create(
        teacher=another_teacher_profile,
        student=student_profile,
        subject=subject,
        class_date=date(2024, 1, 1),
        start_time=time(10, 0),
        end_time=time(11, 0),
    )

    client.force_login(teacher_user)
    url = reverse("teacher_portal:teacher_edit_schedule", kwargs={"schedule_id": schedule.id})
    resp = client.get(url)
    assert resp.status_code == 403
