from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("personal_info", "0017_merge_20250822_1015"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accesslog",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=models.SET_NULL,
                related_name="personal_access_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
