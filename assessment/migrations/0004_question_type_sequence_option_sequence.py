from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0003_question_education_level_stream_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("scale", "Scale (1-5 agreement)"),
                    ("mcq", "Multiple Choice (pick one)"),
                    ("yesno", "Yes / No"),
                ],
                default="scale",
                max_length=10,
                help_text="Controls how options are presented to the user.",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="sequence_order",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Display order within the same education level and dimension.",
            ),
        ),
        migrations.AddField(
            model_name="option",
            name="sequence_order",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Display order of this option within its question.",
            ),
        ),
        migrations.AlterModelOptions(
            name="question",
            options={"ordering": ["education_level", "sequence_order", "id"]},
        ),
        migrations.AlterModelOptions(
            name="option",
            options={"ordering": ["sequence_order", "id"]},
        ),
    ]
