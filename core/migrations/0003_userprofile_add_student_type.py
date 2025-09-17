from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_userprofile_login_lock"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="user_type",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("admin", "管理者"),
                    ("teacher", "講師"),
                    ("student", "生徒"),
                ],
            ),
        ),
    ]
