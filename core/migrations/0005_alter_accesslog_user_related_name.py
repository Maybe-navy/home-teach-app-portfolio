from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_create_accesslog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accesslog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="core_access_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
