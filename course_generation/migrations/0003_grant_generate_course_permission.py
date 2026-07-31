from django.db import migrations

GROUPS = ("School College", "Institute")
PERMISSION_CODENAME = "generate_course"
PERMISSION_NAME = "Can generate AI course details"
CONTENT_TYPE_APP_LABEL = "course_generation"
CONTENT_TYPE_MODEL = "coursegenerationpanel"


def get_or_create_permission(apps):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")

    # Permission/content type may not exist yet (created by post_migrate after
    # migrations run) — create them explicitly so the grant is self-contained.
    content_type, _ = ContentType.objects.get_or_create(
        app_label=CONTENT_TYPE_APP_LABEL,
        model=CONTENT_TYPE_MODEL,
    )
    permission, _ = Permission.objects.get_or_create(
        codename=PERMISSION_CODENAME,
        content_type=content_type,
        defaults={"name": PERMISSION_NAME},
    )
    return permission


def grant_generate_course(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    permission = get_or_create_permission(apps)

    for group_name in GROUPS:
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.permissions.add(permission)


def revoke_generate_course(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")

    content_type = ContentType.objects.filter(
        app_label=CONTENT_TYPE_APP_LABEL,
        model=CONTENT_TYPE_MODEL,
    ).first()
    if not content_type:
        return

    permission = Permission.objects.filter(
        content_type=content_type,
        codename=PERMISSION_CODENAME,
    ).first()
    if not permission:
        return

    for group_name in GROUPS:
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            continue
        group.permissions.remove(permission)


class Migration(migrations.Migration):

    dependencies = [
        ("course_generation", "0002_alter_coursegenerationpanel_options"),
    ]

    operations = [
        migrations.RunPython(grant_generate_course, revoke_generate_course),
    ]
