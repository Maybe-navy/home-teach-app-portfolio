from django.urls import path
from . import views

app_name = "personal_info"

urlpatterns = [
    path('subjects/', views.subject_list, name='subject_list'),
    path('schedule/edit/<int:schedule_id>/', views.edit_schedule_view, name='edit_schedule'),
    path('materials/', views.material_list_view, name='material_list'),
    path('materials/search/', views.material_search_api, name='material_search_api'),
]
