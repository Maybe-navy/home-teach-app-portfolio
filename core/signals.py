from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'user_type': 'admin' if (instance.is_superuser or instance.is_staff) else 'teacher',
                'is_locked': False,
                'failed_login_attempts': 0,
                'is_temporary_password': False,
            }
        )
