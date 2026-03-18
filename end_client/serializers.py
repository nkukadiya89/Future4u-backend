from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from activity_log.models import ActivityLog
from end_client.models import EndClient
from user.models import CustomGroup, User
from utils.datetime_formatter import format_datetime
from utils.generate_ip_address import get_client_ip
from utils.generate_random_password import generate_random_password
from utils.role_permission import create_end_client_role_family


class CreateEndClientSerializer(serializers.ModelSerializer):
    phone = serializers.IntegerField()

    class Meta:
        model = EndClient
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "status",
        ]

    def create(self, validated_data):
        req = self.context.get("request")
        ip_address = get_client_ip(req)
        password = validated_data.pop("password", None)

        if not password:
            password = generate_random_password(self)

        phone = str(validated_data.get("phone", "")).strip()
        if not phone.isdigit():
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid mobile number.",
                }
            )

        user_data = {
            "first_name": validated_data["name"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)
        user.set_password(password)
        end_client_instance = EndClient.objects.create(**validated_data)
        end_client_instance.created_by = None
        end_client_instance.save()
        user.end_client_id = end_client_instance.id
        end_client_id = end_client_instance.id
        result = create_end_client_role_family(req, end_client_id)
        if result["success"]:
            for group in result["end_client_group"]:
                group.user_set.add(user)
        else:
            raise serializers.ValidationError({"success": False, "message": result["message"]})

        try:
            end_client_admin_group = CustomGroup.objects.get(name="EndClient Admin")
            end_client_admin_group.user_set.add(user)
            user.role = end_client_admin_group.id
            user.designation = (
                end_client_admin_group.group_name if end_client_admin_group.group_name else end_client_admin_group.name
            )
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError({"success": False, "message": "End Client Admin group not found"})

        ActivityLog.log.end_client_create(end_client_instance, ip_address, user)
        user.save()

        return end_client_instance


class EndClientSerializer(serializers.ModelSerializer):
    phone = serializers.IntegerField()
    profile_photo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EndClient
        fields = [
            "id",
            "profile_photo",
            "name",
            "email",
            "phone",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        name = data.get("name")
        if self.instance and self.instance.name == name:
            return data
        if EndClient.objects.filter(name=name).exists():
            raise ValidationError(f"Name {name} already exists.")

        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data
        if EndClient.objects.filter(email=email).exists():
            raise ValidationError(f"Email {email} already exists.")

        phone = data.get("phone")
        if self.instance and self.instance.phone == phone:
            return data
        if EndClient.objects.filter(phone=phone).exists():
            raise ValidationError(f"Phone {phone} already exists.")

        return data

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def create(self, validated_data):
        req = self.context.get("request")
        ip_address = get_client_ip(req)
        password = validated_data.pop("password", None)

        if not password:
            password = generate_random_password(self)

        phone = str(validated_data.get("phone", "")).strip()
        # phone = re.sub(r"^(?:\+91|91)", "", phone)
        if not phone.isdigit():
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid mobile number.",
                }
            )

        user_data = {
            "first_name": validated_data["name"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)
        user.set_password(password)
        end_client_instance = EndClient.objects.create(**validated_data)
        end_client_instance.created_by = req.user
        end_client_instance.save()
        user.end_client_id = end_client_instance.id
        end_client_id = end_client_instance.id
        result = create_end_client_role_family(req, end_client_id)
        if result["success"]:
            for group in result["end_client_group"]:
                group.user_set.add(user)
        else:
            raise serializers.ValidationError({"success": False, "message": result["message"]})

        try:
            end_client_admin_group = CustomGroup.objects.get(name="EndClient Admin")
            end_client_admin_group.user_set.add(user)
            user.role = end_client_admin_group.id
            user.designation = (
                end_client_admin_group.group_name if end_client_admin_group.group_name else end_client_admin_group.name
            )
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError({"success": False, "message": "End Client Admin group not found"})

        ActivityLog.log.end_client_create(end_client_instance, ip_address, user)
        user.save()

        return end_client_instance

    def update(self, instance, validated_data):
        req = self.context.get("request")
        ip_address = get_client_ip(req)

        phone = str(validated_data.get("phone", "")).strip()

        if not phone.isdigit():
            raise serializers.ValidationError({"phone": "Please enter a valid mobile number."})

        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.name = validated_data.get("name", instance.name)
        instance.status = validated_data.get("status", instance.status)
        instance.profile_photo = validated_data.get("profile_photo", instance.profile_photo)
        instance.updated_by = req.user
        instance.updated_at = now()

        users = User.objects.filter(end_client_id=instance.id)
        for user in users:
            user.first_name = validated_data.get("name", user.first_name)
            user.email = validated_data.get("email", user.email)
            user.phone = validated_data.get("phone", user.phone)

            user.save()

        ActivityLog.log.end_client_update(instance, ip_address, req.user)

        instance.save()

        return instance


class EndClientInfoSerializer(serializers.ModelSerializer):
    profile_photo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EndClient
        fields = [
            "id",
            "profile_photo",
            "name",
            "email",
            "phone",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        return ret


class EndClientArchiveListSerializer(serializers.ModelSerializer):
    profile_photo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = EndClient
        fields = [
            "id",
            "profile_photo",
            "name",
            "email",
            "phone",
            "status",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
            "deleted",
        ]

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def get_deleted_at(self, obj):
        return format_datetime(getattr(obj, "deleted_at", None))

    def get_deleted_by_name(self, obj):
        return f"{obj.deleted_by.first_name} {obj.deleted_by.last_name}" if obj.deleted_by else None


class EndClientArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = EndClient
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        end_client = []
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        ip_address = get_client_ip(request)

        for deleted_id in deleted_ids:
            try:
                users = User.objects.filter(end_client_id=deleted_id)

                client_instance = EndClient.objects.get(id=deleted_id)

                if client_instance.status == "pending":
                    client_instance.deleted = True
                    client_instance.status = "pending"
                    if hasattr(client_instance, "deleted_by"):
                        client_instance.deleted_by = user
                    if hasattr(client_instance, "deleted_at"):
                        client_instance.deleted_at = now()
                    client_instance.save()
                else:
                    client_instance.status = "inactive"
                    client_instance.deleted = True
                    if hasattr(client_instance, "deleted_by"):
                        client_instance.deleted_by = user
                    if hasattr(client_instance, "deleted_at"):
                        client_instance.deleted_at = now()
                    client_instance.save()

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

                ActivityLog.log.end_client_archive(client_instance, ip_address, users.first())
                end_client.append(client_instance)

            except EndClient.DoesNotExist:
                raise serializers.ValidationError("End Client does not exist")

        return end_client[-1] if end_client else None


class EndClientRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = EndClient
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        end_client = []
        request = self.context.get("request")
        ip_address = get_client_ip(request)

        for deleted_id in deleted_ids:
            try:
                client_instance = EndClient.objects.get(id=deleted_id)
                users = User.objects.filter(end_client=client_instance)

                if client_instance.status == "pending":
                    client_instance.status = "pending"
                    client_instance.deleted = False
                    client_instance.deleted_by = None
                    client_instance.deleted_at = None
                    client_instance.updated_at = now()
                    client_instance.save()
                else:
                    client_instance.status = "active"
                    client_instance.deleted = False
                    client_instance.deleted_by = None
                    client_instance.deleted_at = None
                    client_instance.updated_at = now()
                    client_instance.save()

                # Update all associated users' status and is_active
                if users.exists():
                    for user_instance in users:
                        if user_instance.status == "pending":
                            user_instance.status = "pending"
                            user_instance.is_active = False
                            user_instance.save()
                        else:
                            user_instance.status = "active"
                            user_instance.is_active = True
                            user_instance.save()

                ActivityLog.log.end_client_restore(client_instance, ip_address, users.first())

                end_client.append(client_instance)

            except EndClient.DoesNotExist:
                raise serializers.ValidationError("End Client does not exist")

        return end_client[-1] if end_client else None
