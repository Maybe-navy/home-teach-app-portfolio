from django.conf import settings
from personal_info.models import (
    TeacherStudentAssignment,
    TeacherProfile,
    StudentProfile,
    ClassSchedule,
)


def is_teacher(user) -> bool:
    up = getattr(user, "userprofile", None)
    return bool(up and str(up.user_type).lower().startswith("t"))


def can_teacher_view_student(user, student: StudentProfile) -> bool:
    if not is_teacher(user):
        return False
    if getattr(settings, "TEACHER_VIEW_SCOPE", "assigned") == "all":
        return True
    try:
        tp = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return False
    if TeacherStudentAssignment.objects.filter(teacher=tp, student=student).exists():
        return True
    return ClassSchedule.objects.filter(teacher=tp, student=student).exists()

