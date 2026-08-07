from django.contrib.auth.models import Permission

from company.models import Company
from user.models import AuthGroupPermissionsModel, CustomGroup, RoleFamily
from user.serializers import PermissionSerializers


def parse_ids(value):
    
    if value is None:
        return []
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",") if part.strip()]
    elif not isinstance(value, list):
        return None
    try:
        return [int(item) for item in value]
    except (TypeError, ValueError):
        return None


def get_group_permission_by_user(custom_roles):
    """Return each role's permissions as structured permission objects."""
    user_role_permissions = {}

    for role in custom_roles.select_related("role_family"):
        role_id = role.id
        role_name = role.group_name
        role_family = (
            {"id": role.role_family.id, "name": role.role_family.family_name}
            if role.role_family
            else None
        )

        if role_id not in user_role_permissions:
            user_role_permissions[role_id] = {
                "role_id": role_id,
                "role_name": role_name,
                "role_family": role_family,
                "permissions": [],
            }

        permission_ids = AuthGroupPermissionsModel.objects.filter(
            group_id=role_id
        ).values_list("permission_id", flat=True)
        permissions = Permission.objects.filter(id__in=permission_ids).select_related(
            "content_type"
        )

        for permission in permissions:
            permission_entry = {
                **PermissionSerializers(permission).data,
                "is_checked": True,
            }
            user_role_permissions[role_id]["permissions"].append(permission_entry)

    response = sorted(
        user_role_permissions.values(), key=lambda x: x["role_id"], reverse=False
    )

    return {"roles": response}


def create_company_role_family(request, company_id):
    company_group = []

    manager_family_permissions = [
        "activity_log|Can view activity log",
        "site_location|Can add site location",
        "site_location|Can change site location",
        "site_location|Can delete site location",
        "site_location|Can view site location",
        "employee|Can add employee",
        "employee|Can change employee",
        "employee|Can delete employee",
        "employee|Can view employee",
        "sim_recharge_log|Can add sim recharge log",
        "sim_recharge_log|Can change sim recharge log",
        "sim_recharge_log|Can delete sim recharge log",
        "sim_recharge_log|Can view sim recharge log",
        "device_config|Can add device configuration",
        "device_config|Can view device configuration",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can delete ticket",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can change ticket comment",
        "support_ticket|Can delete ticket comment",
        "support_ticket|Can view ticket comment",
        "user_profile|Can change business setting",
        "user_profile|Can view business setting",
    ]

    sales_manager_permissions = [
        "activity_log|Can view activity log",
        "employee|Can view employee",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "subscription|Can view subscription invoice",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "company|Can view company",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
    ]

    marketing_manager_permissions = [
        "activity_log|Can view activity log",
        "employee|Can view employee",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "company|Can view company",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
        "faq|Can view faq",
        "faq|Can add faq",
        "faq|Can change faq",
    ]

    sales_executive_permissions = [
        "activity_log|Can view activity log",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
    ]

    role_data = [
        # Manager Family
        {
            "name": f"company_{company_id}_Manager",
            "group_name": "Manager",
            "company_id": company_id,
            "role_family": 3,
            "permissions": manager_family_permissions,
        },
        # Sales Manager Family
        {
            "name": f"company_{company_id}_Sales Manager",
            "group_name": "Sales Manager",
            "company_id": company_id,
            "role_family": 3,
            "permissions": sales_manager_permissions,
        },
        # Marketing Manager Family
        {
            "name": f"company_{company_id}_Marketing Manager",
            "group_name": "Marketing Manager",
            "company_id": company_id,
            "role_family": 3,
            "permissions": marketing_manager_permissions,
        },
        # Sales Executive Family
        {
            "name": f"company_{company_id}_Sales Executive",
            "group_name": "Sales Executive",
            "company_id": company_id,
            "role_family": 3,
            "permissions": sales_executive_permissions,
        },
    ]

    for data in role_data:
        try:
            role_family_instance = RoleFamily.objects.get(id=data["role_family"])
        except RoleFamily.DoesNotExist:
            return {"success": False, "message": "Family Not Found"}

        try:
            company_instance = Company.objects.get(id=data["company_id"])
        except Company.DoesNotExist:
            return {"success": False, "message": "Company Not Found"}

        try:
            company_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                company=company_instance,
                role_family=role_family_instance,
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
                        "message": f"Permission '{codename}' not found for app '{app_label}'",
                    }

            company_group.append(company_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "company_group": company_group}


def create_partner_company_role_family(request, partner_company_id):
    # partner_company features removed from the project.
    return {"success": False, "message": "Partner company roles not available"}
    partner_company_group = []

    manager_family_permissions = [
        "activity_log|Can view activity log",
        "employee|Can add employee",
        "employee|Can change employee",
        "employee|Can delete employee",
        "employee|Can view employee",
        "meter_config|Can add meter config",
        "meter_config|Can change meter config",
        "meter_config|Can delete meter config",
        "meter_config|Can view meter config",
        "device_config|Can change device configuration",
        "device_config|Can view device configuration",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can delete ticket",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can change ticket comment",
        "support_ticket|Can delete ticket comment",
        "support_ticket|Can view ticket comment",
    ]

    technician_family_permissions = [
        "activity_log|Can view activity log",
        "device_config|Can add device configuration",
        "device_config|Can change device configuration",
        "device_config|Can view device configuration",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can change ticket comment",
        "support_ticket|Can delete ticket comment",
        "support_ticket|Can view ticket comment",
    ]

    sales_manager_permissions = [
        "activity_log|Can view activity log",
        "employee|Can view employee",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "subscription|Can view subscription invoice",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "company|Can view company",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
    ]

    marketing_manager_permissions = [
        "activity_log|Can view activity log",
        "employee|Can view employee",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "company|Can view company",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
        "faq|Can view faq",
        "faq|Can add faq",
        "faq|Can change faq",
    ]

    sales_executive_permissions = [
        "activity_log|Can view activity log",
        "subscription|Can view subscription",
        "subscription|Can view subscription feature",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can view ticket comment",
        "end_client|Can view end client",
        "partner_company|Can view partner company",
    ]

    role_data = [
        # Manager Family
        {
            "name": f"partner_company_{partner_company_id}_Manager",
            "group_name": "Manager",
            "partner_company_id": partner_company_id,
            "role_family": 2,
            "permissions": manager_family_permissions,
        },
        # Technician Family
        {
            "name": f"partner_company_{partner_company_id}_Technician",
            "group_name": "Technician",
            "partner_company_id": partner_company_id,
            "role_family": 2,
            "permissions": technician_family_permissions,
        },
        # Sales Manager Family
        {
            "name": f"partner_company_{partner_company_id}_Sales Manager",
            "group_name": "Sales Manager",
            "partner_company_id": partner_company_id,
            "role_family": 2,
            "permissions": sales_manager_permissions,
        },
        # Marketing Manager Family
        {
            "name": f"partner_company_{partner_company_id}_Marketing Manager",
            "group_name": "Marketing Manager",
            "partner_company_id": partner_company_id,
            "role_family": 2,
            "permissions": marketing_manager_permissions,
        },
        # Sales Executive Family
        {
            "name": f"partner_company_{partner_company_id}_Sales Executive",
            "group_name": "Sales Executive",
            "partner_company_id": partner_company_id,
            "role_family": 2,
            "permissions": sales_executive_permissions,
        },
    ]

    for data in role_data:
        try:
            role_family_instance = RoleFamily.objects.get(id=data["role_family"])
        except RoleFamily.DoesNotExist:
            return {"success": False, "message": "Family Not Found"}

        try:
            partner_company_instance = PartnerCompany.objects.get(
                id=data["partner_company_id"]
            )
        except PartnerCompany.DoesNotExist:
            return {"success": False, "message": "Partner Company Not Found"}

        try:
            partner_company_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                partner_company=partner_company_instance,
                role_family=role_family_instance,
            )

            for permission in data["permissions"]:
                app_label, codename = permission.split("|")
                try:
                    permission_obj = Permission.objects.get(
                        content_type__app_label=app_label, name=codename
                    )
                    partner_company_wise_group.permissions.add(permission_obj)
                except Permission.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Permission '{codename}' not found for app '{app_label}'",
                    }

            partner_company_group.append(partner_company_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "partner_company_group": partner_company_group}


def create_end_client_role_family(request, end_client_id):
    # end_client features removed from the project.
    return {"success": False, "message": "End client roles not available"}
    end_client_group = []

    manager_family_permissions = [
        "activity_log|Can view activity log",
        "employee|Can add employee",
        "employee|Can change employee",
        "employee|Can delete employee",
        "employee|Can view employee",
        "support_ticket|Can add ticket",
        "support_ticket|Can change ticket",
        "support_ticket|Can delete ticket",
        "support_ticket|Can view ticket",
        "support_ticket|Can add ticket comment",
        "support_ticket|Can change ticket comment",
        "support_ticket|Can delete ticket comment",
        "support_ticket|Can view ticket comment",
        "user_profile|Can change business setting",
        "user_profile|Can view business setting",
    ]

    role_data = [
        # Manager Family
        {
            "name": f"end_client_{end_client_id}_Manager",
            "group_name": "Manager",
            "end_client_id": end_client_id,
            "role_family": 4,
            "permissions": manager_family_permissions,
        },
    ]

    for data in role_data:
        try:
            role_family_instance = RoleFamily.objects.get(id=data["role_family"])
        except RoleFamily.DoesNotExist:
            return {"success": False, "message": "Family Not Found"}

        try:
            end_client_instance = EndClient.objects.get(id=data["end_client_id"])
        except EndClient.DoesNotExist:
            return {"success": False, "message": "EndClient Not Found"}

        try:
            end_client_wise_group = CustomGroup.objects.create(
                name=data["name"],
                group_name=data["group_name"],
                end_client=end_client_instance,
                role_family=role_family_instance,
            )

            for permission in data["permissions"]:
                app_label, codename = permission.split("|")
                try:
                    permission_obj = Permission.objects.get(
                        content_type__app_label=app_label, name=codename
                    )
                    end_client_wise_group.permissions.add(permission_obj)
                except Permission.DoesNotExist:
                    return {
                        "success": False,
                        "message": f"Permission '{codename}' not found for app '{app_label}'",
                    }

            end_client_group.append(end_client_wise_group)
        except Exception as e:
            return {"success": False, "message": str(e)}

    return {"success": True, "end_client_group": end_client_group}
