from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from personal_info.models import TeacherProfile, StudentProfile


def _demo_restrict_delete() -> bool:
    return bool(getattr(settings, "DEMO_READ_ONLY", False))


@receiver(pre_delete, sender=TeacherProfile)
def prevent_delete_teacher_in_demo(sender, instance, using, **kwargs):
    if _demo_restrict_delete():
        raise PermissionDenied("Demo: deleting teacher is not allowed")


@receiver(pre_delete, sender=StudentProfile)
def prevent_delete_student_in_demo(sender, instance, using, **kwargs):
    if _demo_restrict_delete():
        raise PermissionDenied("Demo: deleting student is not allowed")

