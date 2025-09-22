from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import RewardCategory, BillingCategory, StudentProfile


class RewardCategoryModelTests(TestCase):
    def test_str(self):
        cat = RewardCategory.objects.create(category="elementary", reward_per_class=2000)
        self.assertEqual(str(cat), "小学生 : ￥2000")

        custom = RewardCategory.objects.create(category="custom")
        self.assertEqual(str(custom), "金額自由設定 : ￥自由設定")


class BillingCategoryModelTests(TestCase):
    def test_str(self):
        cat = BillingCategory.objects.create(category="junior", fee_per_class=5000)
        self.assertEqual(str(cat), "中学生 : ￥5000")

        custom = BillingCategory.objects.create(category="custom")
        self.assertEqual(str(custom), "金額自由設定 : ￥自由設定")


class StudentProfileCleanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="student1")
        self.default_reward = RewardCategory.objects.create(category="elementary", reward_per_class=2000)
        self.custom_category = RewardCategory.objects.create(category="custom")
        self.custom_billing = BillingCategory.objects.create(category="custom")

    def test_clean_requires_custom_reward(self):
        profile = StudentProfile(
            user=self.user,
            name="テスト",
            gender="man",
            age=10,
            address="住所",
            phone="0000000000",
            email="a@example.com",
            grade="elementary_4",
            reward_category=self.custom_category,
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_clean_accepts_custom_reward(self):
        profile = StudentProfile(
            user=self.user,
            name="テスト",
            gender="man",
            age=10,
            address="住所",
            phone="0000000000",
            email="a@example.com",
            grade="elementary_4",
            reward_category=self.custom_category,
            custom_reward_per_class=3000,
        )
        profile.full_clean()  # Should not raise

    def test_clean_requires_custom_billing(self):
        profile = StudentProfile(
            user=self.user,
            name="テスト",
            gender="man",
            age=10,
            address="住所",
            phone="0000000000",
            email="a@example.com",
            grade="elementary_4",
            billing_category=self.custom_billing,
            reward_category=self.default_reward,
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_clean_accepts_custom_billing(self):
        profile = StudentProfile(
            user=self.user,
            name="テスト",
            gender="man",
            age=10,
            address="住所",
            phone="0000000000",
            email="a@example.com",
            grade="elementary_4",
            billing_category=self.custom_billing,
            custom_billing_per_class=4500,
            reward_category=self.default_reward,
        )
        profile.full_clean()
