from django.core.management.base import BaseCommand
from personal_info.models import ClassSchedule, TeacherStudentAssignment


class Command(BaseCommand):
    help = "既存の授業予定から (teacher, student) の割当を自動生成します"

    def handle(self, *args, **kwargs):
        pairs = (
            ClassSchedule.objects
            .values_list("teacher_id", "student_id")
            .distinct()
        )
        created = 0
        for t_id, s_id in pairs:
            obj, was_created = TeacherStudentAssignment.objects.get_or_create(
                teacher_id=t_id, student_id=s_id
            )
            created += 1 if was_created else 0
        self.stdout.write(self.style.SUCCESS(f"created: {created}"))
