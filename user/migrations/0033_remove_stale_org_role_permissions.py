from django.db import migrations


# Permissions attached to the default org roles in existing databases that
# were removed from the init_data seed lists. (app_label, codename) pairs are
# used because Django codenames are only unique per content type.
STALE_PERMISSIONS = {
    "School College": [
        ("internship_job", "add_internship"),
        ("internship_job", "change_internship"),
        ("internship_job", "delete_internship"),
        ("internship_job", "view_internshipapplication"),
        ("internship_job", "change_internshipapplication"),
        ("internship_job", "view_internship"),
        ("internship_job", "view_job"),
    ],
    "Institute": [
        ("internship_job", "view_job"),
    ],
    "Corporate": [
        ("course", "add_courses"),
        ("course", "change_courses"),
        ("course", "delete_courses"),
        ("course", "view_courseinquiry"),
        ("course", "change_courseinquiry"),
        ("course", "view_courses"),
    ],
}


def _build_permission_lookup(apps):
    """Fetch every stale permission once, keyed by (app_label, codename)."""
    Permission = apps.get_model("auth", "Permission")
    all_pairs = {pair for pairs in STALE_PERMISSIONS.values() for pair in pairs}
    permissions = Permission.objects.filter(
        content_type__app_label__in={pair[0] for pair in all_pairs},
        codename__in={pair[1] for pair in all_pairs},
    )
    return {
        (p.content_type.app_label, p.codename): p
        for p in permissions
    }


def remove_stale_permissions(apps, schema_editor):
    CustomGroup = apps.get_model("user", "CustomGroup")
    lookup = _build_permission_lookup(apps)
    for role_name, perm_pairs in STALE_PERMISSIONS.items():
        role = CustomGroup.objects.filter(name=role_name).first()
        if role is None:
            continue
        for pair in perm_pairs:
            permission = lookup.get(pair)
            if permission is not None:
                role.permissions.remove(permission)


def restore_stale_permissions(apps, schema_editor):
    # Symmetric with the forward op so a rollback restores exactly what this
    # migration removed.
    CustomGroup = apps.get_model("user", "CustomGroup")
    lookup = _build_permission_lookup(apps)
    for role_name, perm_pairs in STALE_PERMISSIONS.items():
        role = CustomGroup.objects.filter(name=role_name).first()
        if role is None:
            continue
        for pair in perm_pairs:
            permission = lookup.get(pair)
            if permission is not None:
                role.permissions.add(permission)


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0032_soft_delete_dead_role_families"),
    ]

    operations = [
        migrations.RunPython(
            remove_stale_permissions,
            restore_stale_permissions,
        ),
    ]
