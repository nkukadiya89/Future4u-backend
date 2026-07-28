import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activity_log", "0003_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove old broken FK columns
        migrations.RemoveField(model_name="activitylog", name="business_category"),
        migrations.RemoveField(model_name="activitylog", name="business_setting"),
        migrations.RemoveField(model_name="activitylog", name="city"),
        migrations.RemoveField(model_name="activitylog", name="company"),
        migrations.RemoveField(model_name="activitylog", name="company_photo"),
        migrations.RemoveField(model_name="activitylog", name="country"),
        migrations.RemoveField(model_name="activitylog", name="employee"),
        migrations.RemoveField(model_name="activitylog", name="faq"),
        migrations.RemoveField(model_name="activitylog", name="state"),
        migrations.RemoveField(model_name="activitylog", name="subscription"),
        migrations.RemoveField(model_name="activitylog", name="subscription_feature"),
        migrations.RemoveField(model_name="activitylog", name="subscription_invoice"),
        # Remove old user FK (will re-add with SET_NULL)
        migrations.RemoveField(model_name="activitylog", name="user"),
        # Remove old fields
        migrations.RemoveField(model_name="activitylog", name="event_type"),
        migrations.RemoveField(model_name="activitylog", name="details"),
        migrations.RemoveField(model_name="activitylog", name="changed_at"),
        migrations.RemoveField(model_name="activitylog", name="ip_address"),
        # Add new clean fields
        migrations.AddField(
            model_name="activitylog",
            name="user",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="event",
            field=models.CharField(max_length=100, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="activitylog",
            name="description",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="activitylog",
            name="entity_type",
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="entity_id",
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="metadata",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="ip_address",
            field=models.GenericIPAddressField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="activitylog",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="activitylog",
            index=models.Index(
                fields=["event", "created_at"], name="actlog_event_created_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="activitylog",
            index=models.Index(
                fields=["user", "created_at"], name="actlog_user_created_idx"
            ),
        ),
        # Update ordering
        migrations.AlterModelOptions(
            name="activitylog",
            options={"ordering": ["-created_at"]},
        ),
    ]
