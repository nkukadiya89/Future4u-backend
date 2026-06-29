import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0028_user_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="deleted",
            field=models.BooleanField(default=False),
        ),

        migrations.AddField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),

        migrations.AddField(
            model_name="user",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users_deleted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        migrations.AddField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),

        migrations.AddField(
            model_name="user",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="users_updated",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]