from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_userprofile_add_student_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("at", models.DateTimeField(auto_now_add=True)),
                ("role", models.CharField(blank=True, max_length=16)),
                ("method", models.CharField(max_length=8)),
                ("path", models.CharField(max_length=512)),
                ("status", models.IntegerField()),
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                ("ua", models.TextField(blank=True)),
                ("referer", models.TextField(blank=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="core_access_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["-at"], name="core_accesslog_at_idx"),
                    models.Index(fields=["path"], name="core_accesslog_path_idx"),
                    models.Index(fields=["status"], name="core_accesslog_status_idx"),
                ],
            },
        ),
    ]
