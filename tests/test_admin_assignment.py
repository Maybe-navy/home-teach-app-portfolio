import codecs
import csv
from io import BytesIO
from django.urls import reverse
from django.contrib.auth.models import User
from personal_info.models import TeacherProfile, StudentProfile, TeacherStudentAssignment
from core.models import UserProfile
import pytest


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
    return TeacherProfile.objects.create(user=u, name=name, gender="man", age=30, address="a", phone="1", email=f"{name}@ex.com", grade="college_1")


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
    return StudentProfile.objects.create(user=u, name=name, gender="man", age=15, address="a", phone="1", email=f"{name}@ex.com", school="", grade="junior_1")


@pytest.mark.django_db
def test_assignment_manage_search_and_bulk_remove(client):
    admin = create_admin_user()
    teacher = create_teacher()
    s1 = create_student("Hanako")
    s2 = create_student("Mika")
    a = TeacherStudentAssignment.objects.create(teacher=teacher, student=s1)

    client.force_login(admin)
    url = reverse("admin_portal:assignment_manage_teacher", kwargs={"teacher_id": teacher.id})
    resp = client.get(url, {"q": "Mi", "only_unassigned": "1"})
    assert resp.status_code == 200
    content = resp.content.decode()
    try:
        select_block = content.split('<select name="student"')[1].split('</select>')[0]
    except IndexError:
        pytest.fail("学生選択セレクトボックスが見つかりません")
    assert "Mika" in select_block
    assert "Hanako" not in select_block

    resp = client.post(url, {"bulk_remove": "1", "ids": [a.id]})
    assert resp.status_code == 302
    assert TeacherStudentAssignment.objects.count() == 0


@pytest.mark.django_db
def test_csv_template_download(client):
    admin = create_admin_user()
    client.force_login(admin)
    url = reverse("admin_portal:assignment_template_csv")
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.content.startswith(codecs.BOM_UTF8)
