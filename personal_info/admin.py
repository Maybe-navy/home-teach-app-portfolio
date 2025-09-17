from django.contrib import admin
from .models import (
    Subject,
    TeacherProfile,
    StudentProfile,
    ClassSchedule,
    ClassKarte,
    DownloadLog,
    AccessLog,
    TeacherStudentAssignment,
)


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ("class_date", "start_time", "end_time", "teacher", "student", "subject")
    list_filter = ("class_date", "teacher", "student", "subject")
    search_fields = ("teacher__name", "student__name", "subject__name")
    date_hierarchy = "class_date"
    list_per_page = 50
    actions = ["export_csv"]

    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="class_schedules.csv"'
        resp.write("\ufeff")
        w = csv.writer(resp)
        w.writerow(["予定日", "開始", "終了", "講師", "生徒", "科目"])
        for sc in queryset.select_related("teacher", "student", "subject"):
            w.writerow([
                sc.class_date,
                sc.start_time,
                sc.end_time,
                getattr(sc.teacher, "name", "-"),
                getattr(sc.student, "name", "-"),
                getattr(sc.subject, "name", "-") if sc.subject else "-",
            ])
        return resp

    export_csv.short_description = "選択した予定をCSV出力"


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "student", "kind", "count")
    list_filter = ("kind", "created_at")
    search_fields = ("user__username", "user__email", "student__name")
    date_hierarchy = "created_at"


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "path", "student", "teacher", "status_code")
    list_filter = ("created_at", "status_code")
    search_fields = ("user__username", "path")


@admin.register(TeacherStudentAssignment)
class TeacherStudentAssignmentAdmin(admin.ModelAdmin):
    list_display = ("teacher", "student")
    search_fields = ("teacher__name", "student__name")
    list_filter = ("teacher",)


admin.site.register((Subject, TeacherProfile, StudentProfile, ClassKarte))

