from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0010_domain_scoring_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="domainreportmeta",
            name="direction_why",
            field=models.TextField(
                blank=True, help_text="One-liner: why this field suits the user"
            ),
        ),
    ]
