from django.urls import path
from .views import (
    login_view, change_password_view
)

app_name = "core"

urlpatterns = [
    path('login/', login_view, name='login'),
    path('change_password/', change_password_view, name='change_password'),
]
