from django.db import models
from django.contrib.auth.models import User
from django.conf import settings



class UserProfile(models.Model):
    class UserType(models.TextChoices):
        ADMIN = "admin", "管理者"
        TEACHER = "teacher", "講師"
        STUDENT = "student", "生徒"

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=10, choices=UserType.choices)
    is_temporary_password = models.BooleanField(default=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    is_locked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_user_type_display()})"


class AccessLog(models.Model):
    """全リクエストのアクセスログ"""

    at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="core_access_logs")
    role = models.CharField(max_length=16, blank=True)
    method = models.CharField(max_length=8)
    path = models.CharField(max_length=512)
    status = models.IntegerField()
    ip = models.GenericIPAddressField(null=True, blank=True)
    ua = models.TextField(blank=True)
    referer = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["-at"], name="core_accesslog_at_idx"),
            models.Index(fields=["path"], name="core_accesslog_path_idx"),
            models.Index(fields=["status"], name="core_accesslog_status_idx"),
        ]

    def __str__(self) -> str:
        u = self.user.username if self.user else "anon"
        return f"{self.at:%Y-%m-%d %H:%M:%S} {u} {self.method} {self.path}"

