from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("domain", "0012_calibrate_parent_acceptance_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="domain_category",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Broad category e.g. healthcare, technology, government, creative_arts",
                max_length=64,
            ),
        ),
    ]
