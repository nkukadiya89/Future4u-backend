from django.contrib.auth.models import Permission

from company.models import Company
from end_client.models import EndClient
from partner_company.models import PartnerCompany
from user.models import (
    AuthGroupPermissionsModel,
    AuthPermissionModel,
    CustomGroup,
    RoleFamily,
)


def get_permission_by_group_ids(group_ids, user_assigned_groups=None, user_assgined_permissions=None):
    permission_dict = {}

    # Fetch all permissions for the assigned user groups
    all_default_permissions = AuthGroupPermissionsModel.objects.filter(group__name=user_assigned_groups)

    for default_permission in all_default_permissions:
        permission = Permission.objects.get(id=default_permission.permission.id)
        permission_detail = {
            "id": None,
            "permission_id": permission.id,
            "name": default_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": default_permission.permission.content_type.id,
            "model_name": default_permission.permission.content_type.app_label.capitalize(),
            "is_checked": False,
        }
        permission_dict[permission.id] = permission_detail

    # Fetch From Given Group ID
    group_ids_permissions = AuthGroupPermissionsModel.objects.filter(group_id__in=group_ids)
    for group_permission in group_ids_permissions:
        permission = Permission.objects.get(id=group_permission.permission.id)
        permission_detail = {
            "id": group_permission.id,
            "permission_id": permission.id,
            "name": group_permission.permission.name,
            "codename": permission.codename,
            "content_type_id": group_permission.permission.content_type.id,
            "model_name": group_permission.permission.content_type.app_label.capitalize(),
            "is_checked": True,
        }
        permission_dict[permission.id] = permission_detail

    # Fetch From Given Employee ID
    if user_assgined_permissions:
        user_assigned_permission_ids = user_assgined_permissions.values_list("id", flat=True)
        user_assigned_permission = Permission.objects.filter(id__in=user_assigned_permission_ids)
        for user_permission in user_assigned_permission:
            permission_detail = {
                "id": None,
                "permission_id": user_permission.id,
                "name": user_permission.name,
                "codename": user_permission.codename,
                "content_type_id": user_permission.content_type.id,
                "model_name": user_permission.content_type.app_label.capitalize(),
                "is_checked": True,
            }
            permission_dict[user_permission.id] = permission_detail

    response = list(permission_dict.values())

    return response


def get_purticlare_permission(content_types, model_names, group_id, company_id, partner_company_id, end_client_id):
    get_all_groups = None
    if company_id:
        try:
            company_instance = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return {"Company Not Found"}

        get_groups = CustomGroup.objects.filter(name__icontains="Company Admin").values_list("name", flat=True)
        get_company_groups = CustomGroup.objects.filter(company=company_instance).values_list("name", flat=True)
        get_all_groups = list(get_groups) + list(get_company_groups)

    elif partner_company_id:
        try:
            partner_company_instance = PartnerCompany.objects.get(id=partner_company_id)
        except PartnerCompany.DoesNotExist:
            return {"Partner Company Not Found"}

        get_groups = CustomGroup.objects.filter(name__icontains="Partner Company Admin").values_list("name", flat=True)
        get_partner_company_groups = CustomGroup.objects.filter(partner_company=partner_company_instance).values_list(
            "name", flat=True
        )
        get_all_groups = list(get_groups) + list(get_partner_company_groups)

    elif end_client_id:
        try:
            end_client_instance = PartnerCompany.objects.get(id=end_client_id)
        except PartnerCompany.DoesNotExist:
            return {"EndClient Not Found"}

        get_groups = CustomGroup.objects.filter(name__icontains="EndClient Admin").values_list("name", flat=True)
        get_end_client_groups = CustomGroup.objects.filter(end_client=end_client_instance).values_list(
            "name", flat=True
        )
        get_all_groups = list(get_groups) + list(get_end_client_groups)

    else:
        get_super_admin_groups = CustomGroup.objects.filter(name__icontains="Super Admin")
        get_all_groups = list(get_super_admin_groups.values_list("name", flat=True))

    permission_list = []

    group_permissions = AuthGroupPermissionsModel.objects.filter(
        permission__content_type=content_types,
        permission__content_type__model=model_names,
        group__name__in=get_all_groups,
    )
    permissions_qs = Permission.objects.filter(id__in=group_permissions.values_list("permission__id", flat=True))

    permission_by_groups = []
    if group_id:
        permission_by_group = AuthGroupPermissionsModel.objects.filter(
            group_id=group_id,
            permission__content_type__id=content_types,
            permission__content_type__model=model_names,
        )
        for permission_group in permission_by_group:
            group_by_permission = {
                "name": permission_group.permission.name,
                "content_type_id": permission_group.permission.content_type.id,
                "is_checked": True,
            }
            permission_by_groups.append(group_by_permission)

    for grp_permission in permissions_qs:
        permission_detail = {
            "id": grp_permission.id,
            "name": grp_permission.name,
            "codename": "codename",
            "content_type_id": grp_permission.content_type.id,
            "model_name": grp_permission.content_type.app_label.capitalize(),
            "is_checked": False,
        }
        permission_list.append(permission_detail)

    if len(permission_by_groups) > 0:
        for permission_by_group in permission_by_groups:
            for permission in permission_list:
                if (
                    permission["name"] == permission_by_group["name"]
                    and permission["content_type_id"] == permission_by_group["content_type_id"]
                ):
                    permission["is_checked"] = True

    return permission_list


def get_group_permission_by_user(custom_group, exclude_group):
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
        permission_by_group = AuthPermissionModel.objects.filter(authgrouppermissionsmodel__group_id=group_id)

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

    response = sorted(user_group_permissions.values(), key=lambda x: x["group_id"], reverse=False)

    return {"user_group_permissions": response}


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
                    permission_obj = Permission.objects.get(content_type__app_label=app_label, name=codename)
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
            partner_company_instance = PartnerCompany.objects.get(id=data["partner_company_id"])
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
                    permission_obj = Permission.objects.get(content_type__app_label=app_label, name=codename)
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
                    permission_obj = Permission.objects.get(content_type__app_label=app_label, name=codename)
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
