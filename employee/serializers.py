from django.contrib.auth.models import Group, Permission
from django.utils.timezone import now
from rest_framework import serializers

from activity_log.models import ActivityLog
from common.mixins.serializer_mixins import (
    DateFieldsMixin,
    DeletedFieldsMixin,
    UserNameMixin,
)
from employee.models import Employee
from user.models import CustomGroup, User
from user.services.registration_service import setup_web_user_password
from utils.generate_ip_address import get_client_ip


class AddEmployeeSerializer(
    DateFieldsMixin, UserNameMixin, serializers.ModelSerializer
):
    password = serializers.CharField(write_only=True, required=False)
    permission = serializers.ListField(write_only=True)
    role = serializers.ListField(write_only=True)
    phone = serializers.IntegerField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    profile_photo = serializers.CharField(required=False, allow_null=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "date_of_joining",
            "alternate_mobile",
            "aadhar_card",
            "pan_card",
            "role",
            "status",
            "password",
            "permission",
            "profile_photo",
            "permanent_address_building",
            "permanent_address_area",
            "permanent_address_landmark",
            "permanent_address_pincode",
            "permanent_address_country",
            "permanent_address_state",
            "permanent_address_city",
            "current_address_building",
            "current_address_area",
            "current_address_landmark",
            "current_address_pincode",
            "current_address_country",
            "current_address_state",
            "current_address_city",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
        ]

    def validate(self, data):
        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data
        if email and (
            User.objects.filter(email=email).exists()
            or Employee.objects.filter(email=email).exists()
        ):
            raise serializers.ValidationError(
                {"email": ["Employee with this email already exists."]}
            )
        phone = data.get("phone")
        if self.instance and self.instance.phone == phone:
            return data
        phone_str = str(phone).strip() if phone is not None else ""
        normalized = phone_str
        if normalized.startswith("+91"):
            normalized = normalized[3:]
        elif normalized.startswith("91") and len(normalized) > 10:
            normalized = normalized[2:]
        if not normalized.isdigit() or len(normalized) != 10:
            raise serializers.ValidationError(
                {"non_field_errors": ["Please enter a valid 10-digit mobile number."]}
            )
        if (
            Employee.objects.filter(phone=normalized).exists()
            or User.objects.filter(phone=normalized).exists()
        ):
            raise serializers.ValidationError(
                {"phone": ["Employee with this phone already exists."]}
            )
        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data.pop("password", None)
        permission_ids = validated_data.pop("permission", [])
        assign_role = validated_data.pop("role", [])

        ip_address = get_client_ip(request)

        phone = str(validated_data.get("phone", "")).strip()
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        if not phone.isdigit() or len(phone) != 10:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid 10-digit mobile number.",
                }
            )

        validated_data["phone"] = phone
        validated_data["created_by"] = request.user
        validated_data.pop("updated_by", None)

        user_data = {
            "first_name": validated_data["first_name"],
            "last_name": validated_data.get("last_name", ""),
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)

        employee_instance = Employee.objects.create(**validated_data)

        if assign_role:
            for role in assign_role:
                try:
                    group = CustomGroup.objects.get(id=role)
                    group.user_set.add(user)
                except Group.DoesNotExist:
                    raise serializers.ValidationError(
                        {"success": False, "message": "Group Not Found"}
                    )

        if permission_ids:
            existing_permissions = Permission.objects.filter(id__in=permission_ids)
            for permission in existing_permissions:
                user.user_permissions.add(permission)

            found_ids = set(existing_permissions.values_list("id", flat=True))
            not_found = set(permission_ids) - found_ids
            if not_found:
                pass

        if employee_instance.created_by:
            user.company = employee_instance.created_by.company
        user.employee = employee_instance
        user.role = assign_role[0] if assign_role else None

        # Set designation from the first assigned role
        if assign_role:
            try:
                group = CustomGroup.objects.get(id=assign_role[0])
                user.designation = group.group_name if group.group_name else group.name
            except CustomGroup.DoesNotExist:
                user.designation = None
        else:
            user.designation = None

        user.save()

        setup_web_user_password(user)

        ActivityLog.log.employee_create(
            employee_instance,
            ip_address,
            request.user,
            request.user.company,
            getattr(request.user, "partner_company", None),
        )

        return employee_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        permission_provided = "permission" in validated_data
        permission_ids = validated_data.pop("permission", [])
        assign_role = validated_data.pop("role", [])

        phone = str(validated_data.get("phone", instance.phone)).strip()
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) > 10:
            phone = phone[2:]
        if not phone.isdigit() or len(phone) != 10:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid 10-digit mobile number.",
                }
            )

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.middle_name = validated_data.get("middle_name", instance.middle_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.date_of_birth = validated_data.get(
            "date_of_birth", instance.date_of_birth
        )
        instance.date_of_joining = validated_data.get(
            "date_of_joining", instance.date_of_joining
        )
        instance.alternate_mobile = validated_data.get(
            "alternate_mobile", instance.alternate_mobile
        )
        instance.aadhar_card = validated_data.get("aadhar_card", instance.aadhar_card)
        instance.pan_card = validated_data.get("pan_card", instance.pan_card)
        instance.role = validated_data.get("role", instance.role)
        instance.status = validated_data.get("status", instance.status)
        instance.profile_photo = validated_data.get(
            "profile_photo", instance.profile_photo
        )
        instance.permanent_address_building = validated_data.get(
            "permanent_address_building", instance.permanent_address_building
        )
        instance.permanent_address_area = validated_data.get(
            "permanent_address_area", instance.permanent_address_area
        )
        instance.permanent_address_landmark = validated_data.get(
            "permanent_address_landmark", instance.permanent_address_landmark
        )
        instance.permanent_address_pincode = validated_data.get(
            "permanent_address_pincode", instance.permanent_address_pincode
        )
        instance.permanent_address_country = validated_data.get(
            "permanent_address_country", instance.permanent_address_country
        )
        instance.permanent_address_state = validated_data.get(
            "permanent_address_state", instance.permanent_address_state
        )
        instance.permanent_address_city = validated_data.get(
            "permanent_address_city", instance.permanent_address_city
        )
        instance.current_address_building = validated_data.get(
            "current_address_building", instance.current_address_building
        )
        instance.current_address_area = validated_data.get(
            "current_address_area", instance.current_address_area
        )
        instance.current_address_landmark = validated_data.get(
            "current_address_landmark", instance.current_address_landmark
        )
        instance.current_address_pincode = validated_data.get(
            "current_address_pincode", instance.current_address_pincode
        )
        instance.current_address_country = validated_data.get(
            "current_address_country", instance.current_address_country
        )
        instance.current_address_state = validated_data.get(
            "current_address_state", instance.current_address_state
        )
        instance.current_address_city = validated_data.get(
            "current_address_city", instance.current_address_city
        )
        instance.updated_by = request.user
        instance.updated_at = now()

        user = User.objects.get(employee=instance)
        if user:
            user.first_name = validated_data.get("first_name", user.first_name)
            user.last_name = validated_data.get("last_name", user.last_name)
            user.email = validated_data.get("email", user.email)
            user.phone = validated_data.get("phone", user.phone)
            user.save()

        if assign_role:
            user.groups.clear()
            for role in assign_role:
                try:
                    group = Group.objects.get(id=role)
                    group.user_set.add(user)
                except Group.DoesNotExist:
                    raise serializers.ValidationError(
                        {"success": False, "message": "Group Not Found"}
                    )

        if permission_provided:
            user.user_permissions.clear()
            if permission_ids:
                existing_permissions = Permission.objects.filter(id__in=permission_ids)
                for permission in existing_permissions:
                    user.user_permissions.add(permission)

                found_ids = set(existing_permissions.values_list("id", flat=True))
                not_found = set(permission_ids) - found_ids
                if not_found:
                    pass

        # Update designation from the assigned role
        if assign_role:
            try:
                group = CustomGroup.objects.get(id=assign_role[0])
                user.designation = group.group_name if group.group_name else group.name
            except CustomGroup.DoesNotExist:
                user.designation = None
        else:
            user.designation = None

        user.save()

        ActivityLog.log.employee_modify(
            instance,
            user,
            request.user.company,
            getattr(request.user, "partner_company", None),
        )

        instance.save()
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        requested_fields = None

        if request:
            fields_param = request.query_params.get("fields")
            if fields_param:
                requested_fields = [field.strip() for field in fields_param.split(",")]

        user = User.objects.get(employee=instance)

        if not requested_fields or "groups" in requested_fields:
            custom_group = user.groups.all()
            if custom_group:
                groups = [
                    {
                        "role": group.id,
                        "role_name": (
                            CustomGroup.objects.filter(id=group.id).first().group_name
                            if CustomGroup.objects.filter(id=group.id).exists()
                            else group.name
                        ),
                    }
                    for group in custom_group
                ]
            else:
                groups = [{"role": None, "role_name": None}]
            ret["groups"] = groups

        if not requested_fields or "permission" in requested_fields:
            permissions = [
                {
                    "id": permission.id,
                    "permission": f"{permission.content_type.app_label} | {permission.name}",
                }
                for permission in user.user_permissions.all()
            ]
            ret["permission"] = permissions

        if not requested_fields or "designation" in requested_fields:
            ret["designation"] = user.designation

        if requested_fields:
            filtered_ret = {}
            for field in requested_fields:
                if field in ret:
                    filtered_ret[field] = ret[field]
            ret = filtered_ret

        return ret


class EmployeeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["status", "updated_by"]

    def update(self, instance, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["updated_by"] = request.user

        if validated_data.get("status") == "inactive":
            instance.status = "inactive"
            if "updated_by" in validated_data:
                instance.updated_by = validated_data["updated_by"]
            instance.updated_at = now()
            instance.save()

            user = User.objects.filter(email=instance.email).first()
            if user:
                user.status = "inactive"
                user.is_active = False
                user.save()

        if validated_data.get("status") == "active":
            instance.status = "active"
            if "updated_by" in validated_data:
                instance.updated_by = validated_data["updated_by"]
            instance.updated_at = now()
            instance.save()

            user = User.objects.get(email=instance.email)
            user.status = "active"
            user.is_active = True
            user.save()

        return instance


class EmployeeArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Employee
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        employees = []
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None

        for deleted_id in deleted_ids:
            try:
                users = User.objects.filter(employee_id=deleted_id)

                employee = Employee.objects.get(id=deleted_id)

                if employee.status == "pending":
                    employee.deleted = True
                    employee.status = "pending"
                    if hasattr(employee, "deleted_by"):
                        employee.deleted_by = user
                    if hasattr(employee, "deleted_at"):
                        employee.deleted_at = now()
                    employee.save()
                else:
                    employee.deleted = True
                    employee.status = "inactive"
                    if hasattr(employee, "deleted_by"):
                        employee.deleted_by = user
                    if hasattr(employee, "deleted_at"):
                        employee.deleted_at = now()
                    employee.save()

                if users.exists():
                    for user_instance in users:
                        if user_instance.status == "pending":
                            user_instance.status = "pending"
                            user_instance.is_active = False
                            user_instance.save()
                        else:
                            user_instance.status = "inactive"
                            user_instance.is_active = False
                            user_instance.save()

                    ip_address = get_client_ip(request) if request else None
                    archiving_user = users.first()
                    company = getattr(archiving_user, "company", None)
                    partner_company = getattr(archiving_user, "partner_company", None)
                    ActivityLog.log.employee_archive(
                        employee, ip_address, archiving_user, company, partner_company
                    )
                employees.append(employee)

            except Employee.DoesNotExist:
                raise serializers.ValidationError("Employee does not exist")

        return employees[-1] if employees else None


class EmployeeRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Employee
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        employees = []
        request = self.context.get("request") if hasattr(self, "context") else None
        for deleted_id in deleted_ids:
            try:
                employee_instance = Employee.objects.get(id=deleted_id)
                users = User.objects.filter(employee=employee_instance)
                if users:
                    for user_instance in users:
                        if user_instance.status == "pending":
                            user_instance.status = "pending"
                            user_instance.is_active = False
                            user_instance.save()
                        else:
                            user_instance.status = "active"
                            user_instance.is_active = True
                            user_instance.save()

                if employee_instance.status == "pending":
                    employee_instance.deleted = False
                    employee_instance.status = "pending"
                    employee_instance.deleted_by = None
                    employee_instance.deleted_at = None
                    employee_instance.updated_at = now()
                    employee_instance.save()
                else:
                    employee_instance.deleted = False
                    employee_instance.status = "active"
                    employee_instance.deleted_by = None
                    employee_instance.deleted_at = None
                    employee_instance.updated_at = now()
                    employee_instance.save()
                if users.exists():
                    ip_address = get_client_ip(request) if request else None
                    restoring_user = users.first()
                    company = getattr(restoring_user, "company", None)
                    partner_company = getattr(restoring_user, "partner_company", None)
                    ActivityLog.log.employee_restore(
                        employee_instance,
                        ip_address,
                        restoring_user,
                        company,
                        partner_company,
                    )
                employees.append(employee_instance)
            except Employee.DoesNotExist:
                continue
        return employees[-1] if employees else None


class EmployeeArchiveListSerializer(
    DateFieldsMixin,
    UserNameMixin,
    DeletedFieldsMixin,
    serializers.ModelSerializer,
):
    password = serializers.CharField(write_only=True, required=False)
    permission = serializers.ListField(write_only=True)
    role = serializers.ListField(write_only=True)
    phone = serializers.IntegerField()
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    profile_photo = serializers.CharField(required=False, allow_null=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "date_of_joining",
            "alternate_mobile",
            "aadhar_card",
            "pan_card",
            "role",
            "status",
            "password",
            "permission",
            "profile_photo",
            "permanent_address_building",
            "permanent_address_area",
            "permanent_address_landmark",
            "permanent_address_pincode",
            "permanent_address_country",
            "permanent_address_state",
            "permanent_address_city",
            "current_address_building",
            "current_address_area",
            "current_address_landmark",
            "current_address_pincode",
            "current_address_country",
            "current_address_state",
            "current_address_city",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
        ]
