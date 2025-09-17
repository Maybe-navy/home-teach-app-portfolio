from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import UserProfile


class Command(BaseCommand):
    help = "Create demo users and minimal sample data (idempotent)."

    def handle(self, *args, **opts):
        User = get_user_model()

        DEMO_PASSWORD = "Demo!Pass1"  # >=10 chars, upper/lower/digit/symbol

        with transaction.atomic():
            # Manager (is_staff=True, is_superuser=False)
            manager, _ = User.objects.get_or_create(
                username="A_demo",
                defaults={"is_staff": True, "is_superuser": False},
            )
            # Always set a known demo password to make login easy
            manager.set_password(DEMO_PASSWORD)
            manager.save()
            # Ensure UserProfile exists and is admin type
            UserProfile.objects.get_or_create(
                user=manager,
                defaults={
                    "user_type": UserProfile.UserType.ADMIN,
                    "is_temporary_password": False,
                    "failed_login_attempts": 0,
                    "is_locked": False,
                },
            )

            # Teacher (read-mostly)
            teacher, _ = User.objects.get_or_create(
                username="T_demo",
                defaults={"is_staff": False, "is_superuser": False},
            )
            teacher.set_password(DEMO_PASSWORD)
            teacher.save()
            # Ensure UserProfile exists (teacher type)
            UserProfile.objects.get_or_create(
                user=teacher,
                defaults={
                    "user_type": UserProfile.UserType.TEACHER,
                    "is_temporary_password": False,
                    "failed_login_attempts": 0,
                    "is_locked": False,
                },
            )

        # TODO: add minimal domain data if required by models.
        # If additional required fields exist on User or related models,
        # please update this command accordingly.

        self.stdout.write(self.style.SUCCESS("Seeded: A_demo / T_demo (password: Demo!Pass1)"))
