from django.urls import path
from . import views

app_name = "student_portal"

urlpatterns = [
    path("my/schedules/", views.my_schedule_list_view, name="my_schedule_list"),
]
