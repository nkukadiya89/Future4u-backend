from django.db import migrations, models
from django.utils import timezone


def copy_date_joined_to_created_at(apps, schema_editor):
    User = apps.get_model("user", "User")
    for user in User.objects.exclude(date_joined__isnull=True).iterator():
        User.objects.filter(pk=user.pk).update(created_at=user.date_joined)


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0026_user_created_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                default=timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(
            copy_date_joined_to_created_at,
            migrations.RunPython.noop,
        ),
    ]
