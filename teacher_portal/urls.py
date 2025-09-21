from django.urls import path
from .views import (
    teacher_dashboard,
    schedule_board_view,
    edit_karte_view,
    create_material_view,
    edit_material_view,
    teacher_edit_schedule_view,
    karte_confirm_confirm_view,
    karte_pdf,
    karte_view,
    student_schedule_list_view,
    student_schedule_pdf_view,
    student_schedule_csv_view,
)

app_name = "teacher_portal"

urlpatterns = [
    path('teacher_dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('schedules/board/', schedule_board_view, name='schedule_board'),
    path(
        "students/<int:student_id>/schedules/",
        student_schedule_list_view,
        name="student_schedule_list",
    ),
    path(
        "students/<int:student_id>/schedules/pdf/",
        student_schedule_pdf_view,
        name="student_schedule_pdf",
    ),
    path(
        "students/<int:student_id>/schedules/csv/",
        student_schedule_csv_view,
        name="student_schedule_csv",
    ),
    path("schedule/<int:schedule_id>/karte/", edit_karte_view, name="karte_input"),
    path(
        "schedule/<int:schedule_id>/karte/confirm/",
        karte_confirm_confirm_view,
        name="karte_confirm_confirm",
    ),
    path('materials/create/', create_material_view, name='teacher_material_create'),
    path('materials/<int:material_id>/edit/', edit_material_view, name='teacher_material_edit'),
    path("schedule/<int:schedule_id>/edit/", teacher_edit_schedule_view, name="teacher_edit_schedule"),
    path('karte/<int:schedule_id>/pdf/', karte_pdf, name='karte_pdf'),
    path('karte/<int:schedule_id>/view/', karte_view, name='karte_view'),
]
