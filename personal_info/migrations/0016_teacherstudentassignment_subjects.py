from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'personal_info',
            '0015_teacherstudentassignment_classschedule_is_absent_and_more',
        ),
        ('personal_info', '0015_accesslog'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherstudentassignment',
            name='subjects',
            field=models.ManyToManyField(blank=True, related_name='ts_assignments', to='personal_info.subject'),
        ),
    ]
