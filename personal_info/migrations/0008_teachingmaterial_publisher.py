from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('personal_info', '0007_classkarte_schedule'),
    ]

    operations = [
        migrations.AddField(
            model_name='teachingmaterial',
            name='publisher',
            field=models.CharField(blank=True, max_length=100, verbose_name='出版社'),
        ),
        migrations.AlterField(
            model_name='teachingmaterial',
            name='title',
            field=models.CharField(max_length=100, unique=True, verbose_name='教材名'),
        ),
    ]
