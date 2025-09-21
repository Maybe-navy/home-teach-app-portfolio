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


@pytest.mark.django_db
def test_admin_can_create_material(client):
    user = User.objects.create_user(username="A700000", password="AdminPass1!")
    profile = user.userprofile
    profile.user_type = "admin"
    profile.is_temporary_password = False
    profile.is_locked = False
    profile.failed_login_attempts = 0
    profile.save(update_fields=["user_type", "is_temporary_password", "is_locked", "failed_login_attempts"])

    client.force_login(user)

    subject = Subject.objects.create(name="英語")

    resp = client.post(
        reverse("admin_portal:material_create"),
        {
            "title": "管理教材",
            "subject": subject.id,
            "grade": "",
            "publisher": "Admin出版社",
        },
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(reverse("personal_info:material_list"))
    assert TeachingMaterial.objects.filter(title="管理教材").exists()


@pytest.mark.django_db
def test_teacher_can_edit_material(client):
    user = User.objects.create_user(username="T800000", password="DemoPass1!")
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

    subject = Subject.objects.create(name="理科")
    material = TeachingMaterial.objects.create(
        title="既存教材",
        subject=subject,
        grade="",
        publisher="旧出版社",
        description="旧説明",
        created_by=user,
    )

    client.force_login(user)

    next_url = reverse("teacher_portal:schedule_board")
    resp = client.post(
        reverse("teacher_portal:teacher_material_edit", args=[material.id]),
        {
            "title": "既存教材（更新）",
            "subject": subject.id,
            "grade": "junior_1",
            "publisher": "新出版社",
            "description": "更新後の説明",
            "next": next_url,
        },
    )

    assert resp.status_code == 302
    assert resp.url == next_url
    material.refresh_from_db()
    assert material.title == "既存教材（更新）"
    assert material.publisher == "新出版社"
    assert material.description == "更新後の説明"
    assert material.get_grade_display() == "中学１年生"


@pytest.mark.django_db
def test_admin_can_edit_material(client):
    user = User.objects.create_user(username="A800000", password="AdminPass1!")
    profile = user.userprofile
    profile.user_type = "admin"
    profile.is_temporary_password = False
    profile.is_locked = False
    profile.failed_login_attempts = 0
    profile.save(update_fields=["user_type", "is_temporary_password", "is_locked", "failed_login_attempts"])

    client.force_login(user)

    subject = Subject.objects.create(name="国語")
    material = TeachingMaterial.objects.create(
        title="編集対象",
        subject=subject,
        grade="junior_1",
        publisher="旧出版社",
        description="旧説明",
        created_by=user,
    )

    resp = client.post(
        reverse("admin_portal:material_edit", args=[material.id]),
        {
            "title": "編集済み教材",
            "subject": subject.id,
            "grade": "junior_2",
            "publisher": "新出版社",
            "description": "新しい説明",
        },
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith(reverse("personal_info:material_list"))
    material.refresh_from_db()
    assert material.title == "編集済み教材"
    assert material.publisher == "新出版社"
    assert material.description == "新しい説明"
    assert material.get_grade_display() == "中学２年生"
