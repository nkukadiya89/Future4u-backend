from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education_level', '0003_educationlevel_fallback_messages'),
    ]

    operations = [
        migrations.AddField(
            model_name='educationlevel',
            name='next_step_1',
            field=models.TextField(blank=True, help_text='First recommended next step for this level'),
        ),
        migrations.AddField(
            model_name='educationlevel',
            name='next_step_2',
            field=models.TextField(blank=True, help_text='Second recommended next step for this level'),
        ),
        migrations.AddField(
            model_name='educationlevel',
            name='next_step_3',
            field=models.TextField(blank=True, help_text='Third recommended next step for this level'),
        ),
    ]
