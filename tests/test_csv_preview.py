import io
from django.urls import reverse
from django.contrib.auth.models import User
from personal_info.models import TeacherProfile, StudentProfile, TeacherStudentAssignment
from core.models import UserProfile
import pytest


def make_user(username, user_type):
    u = User.objects.create_user(username=username, password="pw")
    UserProfile.objects.update_or_create(
        user=u,
        defaults={
            "user_type": user_type,
            "is_locked": False,
            "failed_login_attempts": 0,
            "is_temporary_password": False,
        },
    )
    return u


def make_teacher():
    u = make_user("teacher1", "teacher")
    return TeacherProfile.objects.create(user=u, name="T", gender="man", age=30, address="a", phone="1", email="t@ex.com", grade="college_1")


def make_student():
    u = make_user("student1", "student")
    return StudentProfile.objects.create(user=u, name="S", gender="man", age=15, address="a", phone="1", email="s@ex.com", school="", grade="junior_1")


def make_admin():
    return make_user("admin1", "admin")


@pytest.mark.django_db
def test_preview_and_confirm(client):
    admin = make_admin()
    teacher = make_teacher()
    student = make_student()
    client.force_login(admin)
    url = reverse("admin_portal:assignment_bulk")

    csvdata = f"teacher_id,student_id\n{teacher.id},{student.id}\n999,999\n"
    f = io.BytesIO(csvdata.encode("utf-8"))
    f.name = "a.csv"
    resp = client.post(url, {"preview": "1", "file": f})
    assert resp.status_code == 200
    ctx = resp.context
    assert ctx is not None, "プレビュー画面のコンテキストが取得できません"
    statuses = [row["status"] for row in ctx["rows"]]
    assert "ERROR" in statuses
    assert ctx["has_error"] is True

    resp = client.post(url, {"confirm": "1", "csvdata": csvdata})
    assert resp.status_code == 302
    assert TeacherStudentAssignment.objects.count() == 0

    csvdata2 = f"teacher_id,student_id\n{teacher.id},{student.id}\n"
    f2 = io.BytesIO(csvdata2.encode("utf-8"))
    f2.name = "b.csv"
    resp = client.post(url, {"preview": "1", "file": f2})
    assert resp.status_code == 200
    resp = client.post(url, {"confirm": "1", "csvdata": csvdata2})
    assert resp.status_code == 302
    assert TeacherStudentAssignment.objects.count() == 1
