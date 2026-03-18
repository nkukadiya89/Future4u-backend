from django.contrib.auth.models import Permission

from user.models import AuthGroupPermissionsModel, AuthPermissionModel, CustomGroup
from vendor.models import Vendor


def get_permission_by_group_ids(
    group_ids, user_assigned_groups=None, user_assgined_permissions=None
):
    permission_dict = {}

    # Fetch all permissions for the assigned user groups
    all_default_permissions = AuthGroupPermissionsModel.objects.filter(
        group__name=user_assigned_groups
    )

    for default_permission in all_default_permissions:
        permission = Permission.objects.get(id=default_permission.permission.id)
        permission_detail = {
            "id": None,
            "permission_id": permission.id,  # type: ignore
            "name": default_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": default_permission.permission.content_type.id,
            "model_name": (
                default_permission.permission.content_type.app_label.capitalize()
            ),
            "is_checked": False,
        }
        permission_dict[permission.id] = permission_detail  # type: ignore

    # Fetch From Given Group ID
    group_ids_permissions = AuthGroupPermissionsModel.objects.filter(
        group_id__in=group_ids
    )
    for group_permission in group_ids_permissions:
        permission = Permission.objects.get(id=group_permission.permission.id)
        permission_detail = {
            "id": group_permission.id,
            "permission_id": permission.id,  # type: ignore
            "name": group_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": group_permission.permission.content_type.id,
            "model_name": group_permission.permission.content_type.app_label.capitalize(),
            "is_checked": True,
        }
        permission_dict[permission.id] = permission_detail  # type: ignore

    # Fetch From Given Employee ID
    if user_assgined_permissions:
        user_assigned_permission_ids = user_assgined_permissions.values_list(
            "id", flat=True
        )
        user_assigned_permission = Permission.objects.filter(
            id__in=user_assigned_permission_ids
        )
        for user_permission in user_assigned_permission:
            permission_detail = {
                "id": None,
                "permission_id": user_permission.id,  # type: ignore
                "name": user_permission.name,
                "codename": user_permission.codename,
                "content_type_id": user_permission.content_type.id,
                "model_name": user_permission.content_type.app_label.capitalize(),
                "is_checked": True,
            }
            permission_dict[user_permission.id] = permission_detail  # type: ignore

    response = list(permission_dict.values())

    return response


def get_group_permission_by_user(custom_group, exclude_group=None):
    user_group_permissions = {}

    for group in custom_group:
        group_id = group.id
        custom_group_name = group.group_name
        group_role_family = group.role_family.family_name if group.role_family else None

        if group_id not in user_group_permissions:
            user_group_permissions[group_id] = {
                "group_id": group_id,
                "group_role_family": group_role_family,
                "group_name": custom_group_name,
                "permissions": [],
            }

        # Get only the permissions for this CustomGroup
        permission_by_group = AuthPermissionModel.objects.filter(
            authgrouppermissionsmodel__group_id=group_id
        )

        for permission_group in permission_by_group:
            group_permission = AuthGroupPermissionsModel.objects.filter(
                permission=permission_group, group_id=group_id
            ).first()

            permission_entry = {
                "id": group_permission.id if group_permission else None,
                "permission_id": permission_group.id,
                "name": permission_group.name,
                "model_name": (
                    "RFQ"
                    if permission_group.content_type.app_label.capitalize() == "Rfq"
                    else permission_group.content_type.app_label.capitalize()
                ),
                "is_checked": True,
            }
            user_group_permissions[group_id]["permissions"].append(permission_entry)

    # Convert dictionary to list and sort in ascending order based on 'group_id'
    response = sorted(
        user_group_permissions.values(), key=lambda x: x["group_id"], reverse=False
    )

    return {"user_group_permissions": response}


def create_vendor_role(vendor_id):
    vendor_group = []
    sales_manager = [
        "rfq|Can view float rfq",
        "rfq|Can view rfq",
        "rfq|Can view rfq material detail",
        "rfq|Can view rfq vendor detail",
        "rfq|Can add rfq vendor assign sales manager",
        "rfq|Can change rfq vendor assign sales manager",
        "rfq|Can delete rfq vendor assign sales manager",
        "rfq|Can view rfq vendor assign sales manager",
        "rfq|Can add bid rfq",
        "rfq|Can change bid rfq",
        "rfq|Can delete bid rfq",
        "rfq|Can view bid rfq",
    ]

    role_data = [
        {
            "name": f"vendor_{vendor_id}_SalesManager",
            "group_name": "Sales Manager",
            "vendor_id": vendor_id,
            "permissions": sales_manager,
        }
    ]
    for data in role_data:
        try:
            vendor_instance = Vendor.objects.get(id=data["vendor_id"])
        except Vendor.DoesNotExist:
            return {"success": False, "message": "Vendor Not Found"}
        try:
            company_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                vendor=vendor_instance,
            )

            for permission in data["permissions"]:
                app_label, codename = permission.split("|")
                try:
                    permission_obj = Permission.objects.get(
                        content_type__app_label=app_label, name=codename
                    )
                    company_wise_group.permissions.add(permission_obj)
                except Permission.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Permission '{codename}' not "
                        f"found for app '{app_label}'",
                    }

            vendor_group.append(company_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "vendor_group": vendor_group}
