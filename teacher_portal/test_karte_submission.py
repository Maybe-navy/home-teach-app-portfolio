import datetime as dt

from django.test import TestCase, Client
from django.urls import reverse

from django.contrib.auth.models import User
from personal_info.models import TeacherProfile, StudentProfile, ClassSchedule


class KarteSubmitFlowTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_karte_submit_confirms_and_blocks_edit(self):
        # Create teacher user and profile
        t_user = User.objects.create_user(username="t1", password="pass")
        t_profile = TeacherProfile.objects.create(
            user=t_user,
            name="Teacher One",
            gender="man",
            age=25,
            address="addr",
            phone="000-0000-0000",
            email="t1@example.com",
            grade="college_4",
        )

        # Create student user and profile
        s_user = User.objects.create_user(username="s1", password="pass")
        s_profile = StudentProfile.objects.create(
            user=s_user,
            name="Student One",
            gender="man",
            age=12,
            address="addr",
            phone="000-0000-0000",
            email="s1@example.com",
            grade="junior_1",
        )

        # Class schedule (assigned to teacher)
        sc = ClassSchedule.objects.create(
            teacher=t_profile,
            student=s_profile,
            class_date=dt.date.today(),
            start_time=dt.time(10, 0),
            end_time=dt.time(11, 0),
        )

        self.client.force_login(t_user)

        # First GET to ensure karte exists
        url = reverse("teacher_portal:karte_input", args=[sc.id])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        # Submit the karte (not draft)
        payload = {
            "karte_summary": "summary",
            "karte_detail": "detail",
            "tardy": False,
            "evaluation": "good",
        }
        r = self.client.post(url, data=payload, follow=True)
        self.assertEqual(r.status_code, 200)

        # Reload schedule; should be marked as done
        sc.refresh_from_db()
        self.assertEqual(sc.status, ClassSchedule.STATUS_DONE)

        # Further edit attempt should be forbidden (confirmed karte)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

