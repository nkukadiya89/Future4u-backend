from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education_level', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='educationlevel',
            name='fallback_insight',
            field=models.TextField(blank=True, help_text='Shown when user has insufficient responses for this level'),
        ),
        migrations.AddField(
            model_name='educationlevel',
            name='fallback_action',
            field=models.TextField(blank=True, help_text='Action prompt shown alongside fallback insight'),
        ),
    ]
