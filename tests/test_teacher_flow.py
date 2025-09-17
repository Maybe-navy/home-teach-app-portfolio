from datetime import date, time
from django.urls import reverse
from django.contrib.auth.models import User
from personal_info.models import TeacherProfile, StudentProfile, Subject, TeacherStudentAssignment, ClassSchedule
from core.models import UserProfile
import pytest


def create_user(username, user_type):
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


def create_teacher(username="teacher"):
    u = create_user(username, "teacher")
    return TeacherProfile.objects.create(user=u, name=username, gender="man", age=30, address="a", phone="1", email=f"{username}@ex.com", grade="college_1")


def create_student(username="student"):
    u = create_user(username, "student")
    return StudentProfile.objects.create(user=u, name=username, gender="man", age=15, address="a", phone="1", email=f"{username}@ex.com", school="", grade="junior_1")


@pytest.mark.django_db
def test_teacher_flow(client):
    teacher = create_teacher()
    student = create_student("student1")
    subject = Subject.objects.create(name="Math")
    TeacherStudentAssignment.objects.create(teacher=teacher, student=student)
    ClassSchedule.objects.create(teacher=teacher, student=student, subject=subject, class_date=date.today(), start_time=time(10,0), end_time=time(11,0))

    client.force_login(teacher.user)
    list_url = reverse("teacher_portal:student_schedule_list", kwargs={"student_id": student.id})
    resp = client.get(list_url)
    assert resp.status_code == 200
    assert client.get(reverse("teacher_portal:student_schedule_csv", kwargs={"student_id": student.id})).status_code == 200
    assert client.get(reverse("teacher_portal:student_schedule_pdf", kwargs={"student_id": student.id})).status_code == 200

    other = create_student("other")
    list_url2 = reverse("teacher_portal:student_schedule_list", kwargs={"student_id": other.id})
    assert client.get(list_url2).status_code == 403

    board = client.get(reverse("teacher_portal:schedule_board"), {"q": "other"})
    assert board.status_code == 200
    token = None
    for result in board.context["student_search_results"]:
        if result["student"].id == other.id:
            token = result["access_token"]
            break
    assert token, "検索結果からアクセス用トークンが取得できません"

    resp = client.get(f"{list_url2}?access={token}")
    assert resp.status_code == 200
    assert resp.context["viewing_via_search"] is True
