# Generated for the 12-MCQ-only assessment flow.

from django.db import migrations, models


def remove_text_questions(apps, schema_editor):
    Question = apps.get_model("assessment", "Question")
    Question.objects.filter(question_type="text").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0028_userresponse_text_answer_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_text_questions, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="userresponse",
            name="text_answer",
        ),
        migrations.AlterField(
            model_name="question",
            name="question_type",
            field=models.CharField(
                choices=[
                    ("scale", "Scale (1-5 agreement)"),
                    ("mcq", "Multiple Choice (pick one)"),
                    ("yesno", "Yes / No"),
                ],
                default="scale",
                help_text="Controls how options are presented to the user.",
                max_length=10,
            ),
        ),
    ]
