from django.db import migrations

DEAD_FAMILY_NAMES = (
    "Partner Company Family",
    "Ads Agency Family",
    "EndClient Family",
)


def soft_delete_dead_role_families(apps, schema_editor):
    RoleFamily = apps.get_model("user", "RoleFamily")
    RoleFamily.objects.filter(family_name__in=DEAD_FAMILY_NAMES, deleted=False).update(
        deleted=True
    )


def restore_dead_role_families(apps, schema_editor):
    RoleFamily = apps.get_model("user", "RoleFamily")
    # Only restore families this migration soft-deleted (symmetric with the
    # forward op) so a rollback cannot un-delete a family that was already
    # soft-deleted for an unrelated reason.
    RoleFamily.objects.filter(family_name__in=DEAD_FAMILY_NAMES, deleted=True).update(
        deleted=False
    )


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0031_user_is_org_staff"),
    ]

    operations = [
        migrations.RunPython(
            soft_delete_dead_role_families,
            restore_dead_role_families,
        ),
    ]
