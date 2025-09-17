from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ("personal_info", "0018_alter_accesslog_user_related_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="classschedule",
            name="teacher",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="personal_info.teacherprofile"),
        ),
        migrations.AlterField(
            model_name="classschedule",
            name="class_date",
            field=models.DateField(blank=True, null=True, verbose_name="授業日"),
        ),
        migrations.AlterField(
            model_name="classschedule",
            name="start_time",
            field=models.TimeField(blank=True, null=True, verbose_name="授業開始時刻"),
        ),
        migrations.AlterField(
            model_name="classschedule",
            name="end_time",
            field=models.TimeField(blank=True, null=True, verbose_name="授業終了時刻"),
        ),
        migrations.AlterField(
            model_name="classschedule",
            name="status",
            field=models.CharField(choices=[("pending", "保留"), ("scheduled", "未実施"), ("done", "実施済")], db_index=True, default="pending", max_length=10, verbose_name="状態"),
        ),
        migrations.AddField(
            model_name="classkarte",
            name="is_confirmed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="classkarte",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="classkarte",
            name="confirmed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="confirmed_kartes", to="personal_info.teacherprofile"),
        ),
    ]
