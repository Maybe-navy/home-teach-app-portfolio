import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from personal_info.models import Subject, TeacherProfile, TeachingMaterial


@pytest.mark.django_db
def test_teacher_can_create_material_in_demo(client, settings):
    settings.DEMO_READ_ONLY = True

    user = User.objects.create_user(username="T700000", password="DemoPass1!")
    profile = user.userprofile
    profile.user_type = "teacher"
    profile.is_temporary_password = False
    profile.is_locked = False
    profile.failed_login_attempts = 0
    profile.save(update_fields=["user_type", "is_temporary_password", "is_locked", "failed_login_attempts"])

    TeacherProfile.objects.get_or_create(
        user=user,
        defaults={
            "name": "テスト講師",
            "gender": "man",
            "age": 25,
            "address": "demo",
            "phone": "000-0000-0000",
            "email": "teacher@example.com",
            "school": "demo",
            "grade": "college_1",
        },
    )

    client.force_login(user)

    subject = Subject.objects.create(name="数学")

    resp = client.post(
        reverse("teacher_portal:teacher_material_create"),
        {
            "title": "デモ教材",
            "subject": subject.id,
            "grade": "",
            "publisher": "Demo出版社",
            "next": reverse("teacher_portal:schedule_board"),
        },
    )

    assert resp.status_code == 302
    assert TeachingMaterial.objects.filter(title="デモ教材").exists()
