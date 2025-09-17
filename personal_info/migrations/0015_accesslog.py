from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("personal_info", "0014_downloadlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.CharField(max_length=255)),
                ("method", models.CharField(max_length=16)),
                ("status_code", models.IntegerField(default=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "student",
                    models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="personal_info.studentprofile"),
                ),
                (
                    "teacher",
                    models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, to="personal_info.teacherprofile"),
                ),
                (
                    "user",
                    models.ForeignKey(null=True, on_delete=models.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
