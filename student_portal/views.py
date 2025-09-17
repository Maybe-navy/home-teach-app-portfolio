from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from personal_info.models import StudentProfile, ClassSchedule


def is_student(user) -> bool:
    up = getattr(user, "userprofile", None)
    return bool(up and str(up.user_type).lower().startswith("s"))


@login_required
def my_schedule_list_view(request):
    sp = get_object_or_404(StudentProfile, user=request.user)
    qs = (
        ClassSchedule.objects
        .filter(student=sp)
        .select_related("teacher", "student", "subject")
        .order_by("class_date", "start_time")
    )
    return render(
        request,
        "student_portal/my_schedule_list.html",
        {"student": sp, "schedules": qs, "is_student": True},
    )
