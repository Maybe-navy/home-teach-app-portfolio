import contextlib
import os
import sys
import threading

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from personal_info.models import TeacherProfile, StudentProfile


_state = threading.local()


def _demo_override_enabled() -> bool:
    return bool(getattr(_state, "allow_delete", False))


@contextlib.contextmanager
def demo_delete_override():
    previous = getattr(_state, "allow_delete", False)
    _state.allow_delete = True
    try:
        yield
    finally:
        _state.allow_delete = previous


def _demo_restrict_delete() -> bool:
    if getattr(settings, "DEMO_READ_ONLY_BYPASS", False):
        return False
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return False
    if _demo_override_enabled():
        return False
    return bool(getattr(settings, "DEMO_READ_ONLY", False))


@receiver(pre_delete, sender=TeacherProfile)
def prevent_delete_teacher_in_demo(sender, instance, using, **kwargs):
    if _demo_restrict_delete():
        raise PermissionDenied("Demo: deleting teacher is not allowed")


@receiver(pre_delete, sender=StudentProfile)
def prevent_delete_student_in_demo(sender, instance, using, **kwargs):
    if _demo_restrict_delete():
        raise PermissionDenied("Demo: deleting student is not allowed")
