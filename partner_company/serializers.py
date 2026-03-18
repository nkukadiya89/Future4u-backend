import re

from django.utils.timezone import now
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from activity_log.models import ActivityLog
from city.models import City
from city_areas.models import CityArea
from country.models import Country
from state.models import State
from user.models import CustomGroup, User
from utils.datetime_formatter import format_datetime
from utils.generate_ip_address import get_client_ip
from utils.generate_random_password import generate_random_password
from utils.role_permission import create_partner_company_role_family

from .models import PartnerCompany, PartnerCompanyDocument


class PartnerCompanySerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    phone = serializers.IntegerField()
    partner_company_logo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    gst_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    gst_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    gst_address_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    gst_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )
    communication_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    communication_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    communication_address_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    communication_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )

    gst_address_country_name = serializers.CharField(source="gst_address_country.name", read_only=True)
    gst_address_state_name = serializers.CharField(source="gst_address_state.name", read_only=True)
    gst_address_city_name = serializers.CharField(source="gst_address_city.name", read_only=True)
    gst_address_area_name = serializers.CharField(source="gst_address_area.city_area_name", read_only=True)
    communication_address_country_name = serializers.CharField(
        source="communication_address_country.name", read_only=True
    )
    communication_address_state_name = serializers.CharField(source="communication_address_state.name", read_only=True)
    communication_address_city_name = serializers.CharField(source="communication_address_city.name", read_only=True)
    communication_address_area_name = serializers.CharField(
        source="communication_address_area.city_area_name", read_only=True
    )

    class Meta:
        model = PartnerCompany
        fields = [
            "id",
            "partner_company_logo",
            "gst_no",
            "company_name",
            "person_name",
            "email",
            "phone",
            "password",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_area",
            "gst_address_area_name",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_country_name",
            "communication_address_state",
            "communication_address_state_name",
            "communication_address_city",
            "communication_address_city_name",
            "communication_address_building",
            "communication_address_area",
            "communication_address_area_name",
            "communication_address_landmark",
            "communication_address_pincode",
            "status",
            "is_active",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        errors = {}
        instance = getattr(self, "instance", None)

        company_name = data.get("company_name", None)
        if company_name is not None:
            qs = PartnerCompany.objects.filter(company_name=company_name)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                errors["company_name"] = f"Partner Company with this Name {company_name} already exists."

        email = data.get("email", None)
        if email is not None:
            pc_qs = PartnerCompany.objects.filter(email=email)
            if instance:
                pc_qs = pc_qs.exclude(pk=instance.pk)
            email_changed = not (instance and instance.email == email)
            if pc_qs.exists() or (email_changed and User.objects.filter(email=email).exists()):
                errors["email"] = f"Partner Company with this Email {email} already exists."

        phone = data.get("phone", None)
        if phone is not None and instance is None:
            pc_qs = PartnerCompany.objects.filter(phone=phone)
            if pc_qs.exists() or User.objects.filter(phone=phone).exists():
                errors["phone"] = f"Partner Company with this Phone {phone} already exists."

        gst_no = data.get("gst_no", None)
        if gst_no:
            qs = PartnerCompany.objects.filter(gst_no=gst_no)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                errors["gst_no"] = f"Partner Company with this GST Number {gst_no} already exists."

        if errors:
            raise ValidationError(errors)

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
        phone = re.sub(r"^(?:\+91|91)", "", phone)
        if not phone.isdigit() or len(phone) != 10:
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid 10-digit mobile number.",
                }
            )

        user_data = {
            "first_name": validated_data["person_name"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "emergency_contact": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)
        user.set_password(password)
        partner_company_instance = PartnerCompany.objects.create(
            created_by=getattr(req, "user", None),
            **validated_data,
        )
        user.partner_company = partner_company_instance
        partner_company_id = partner_company_instance.id
        result = create_partner_company_role_family(req, partner_company_id)
        if result["success"]:
            for group in result["partner_company_group"]:
                group.user_set.add(user)
        else:
            raise serializers.ValidationError({"success": False, "message": result["message"]})
        try:
            partner_company_admin_group = CustomGroup.objects.get(name="Partner Company Admin")
            partner_company_admin_group.user_set.add(user)
            user.role = partner_company_admin_group.id
            user.designation = (
                partner_company_admin_group.group_name
                if partner_company_admin_group.group_name
                else partner_company_admin_group.name
            )
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError({"success": False, "message": "Partner Company Admin group not found"})

        ActivityLog.log.partner_company_create(partner_company_instance, ip_address, user)
        user.save()

        return partner_company_instance

    def update(self, instance, validated_data):
        req = self.context.get("request")

        phone = validated_data.get("phone", None)
        if phone is not None:
            phone = str(phone).strip()
            phone = re.sub(r"^(?:\+91|91)", "", phone)
            if not phone.isdigit() or len(phone) != 10:
                raise serializers.ValidationError({"phone": "Please enter a valid 10-digit mobile number."})

        old_email = instance.email
        old_phone = instance.phone

        instance.person_name = validated_data.get("person_name", instance.person_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.company_name = validated_data.get("company_name", instance.company_name)
        instance.gst_no = validated_data.get("gst_no", instance.gst_no)
        instance.status = validated_data.get("status", instance.status)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.partner_company_logo = validated_data.get("partner_company_logo", instance.partner_company_logo)

        # GST Address fields
        instance.gst_address_country = validated_data.get("gst_address_country", instance.gst_address_country)
        instance.gst_address_state = validated_data.get("gst_address_state", instance.gst_address_state)
        instance.gst_address_city = validated_data.get("gst_address_city", instance.gst_address_city)
        instance.gst_address_building = validated_data.get("gst_address_building", instance.gst_address_building)
        instance.gst_address_area = validated_data.get("gst_address_area", instance.gst_address_area)
        instance.gst_address_landmark = validated_data.get("gst_address_landmark", instance.gst_address_landmark)
        instance.gst_address_pincode = validated_data.get("gst_address_pincode", instance.gst_address_pincode)

        # Communication Address fields
        instance.communication_address_country = validated_data.get(
            "communication_address_country", instance.communication_address_country
        )
        instance.communication_address_state = validated_data.get(
            "communication_address_state", instance.communication_address_state
        )
        instance.communication_address_city = validated_data.get(
            "communication_address_city", instance.communication_address_city
        )
        instance.communication_address_building = validated_data.get(
            "communication_address_building", instance.communication_address_building
        )
        instance.communication_address_area = validated_data.get(
            "communication_address_area", instance.communication_address_area
        )
        instance.communication_address_landmark = validated_data.get(
            "communication_address_landmark", instance.communication_address_landmark
        )
        instance.communication_address_pincode = validated_data.get(
            "communication_address_pincode", instance.communication_address_pincode
        )
        instance.updated_by = req.user

        users = User.objects.filter(partner_company=instance)
        for user in users:
            if "person_name" in validated_data:
                user.first_name = validated_data["person_name"]
            if "email" in validated_data and user.email == old_email:
                user.email = validated_data["email"]
            if "phone" in validated_data and user.phone == old_phone:
                user.phone = validated_data["phone"]

            user.save()

        # set updated_at timestamp on update
        instance.updated_at = now()
        ip_address = get_client_ip(req)
        ActivityLog.log.partner_company_update(instance, ip_address, req.user)

        instance.save()

        return instance


class PartnerCompanyInfoSerializer(serializers.ModelSerializer):
    partner_company_logo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    gst_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    gst_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    gst_address_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    gst_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )
    communication_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    communication_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    communication_address_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    communication_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )

    # Read-only fields for names
    gst_address_country_name = serializers.CharField(source="gst_address_country.name", read_only=True)
    gst_address_state_name = serializers.CharField(source="gst_address_state.name", read_only=True)
    gst_address_city_name = serializers.CharField(source="gst_address_city.name", read_only=True)
    gst_address_area_name = serializers.CharField(source="gst_address_area.city_area_name", read_only=True)
    communication_address_country_name = serializers.CharField(
        source="communication_address_country.name", read_only=True
    )
    communication_address_state_name = serializers.CharField(source="communication_address_state.name", read_only=True)
    communication_address_city_name = serializers.CharField(source="communication_address_city.name", read_only=True)
    communication_address_area_name = serializers.CharField(
        source="communication_address_area.city_area_name", read_only=True
    )

    class Meta:
        model = PartnerCompany
        fields = [
            "id",
            "company_name",
            "person_name",
            "gst_no",
            "email",
            "phone",
            "status",
            "is_active",
            "partner_company_logo",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_area",
            "gst_address_area_name",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_country_name",
            "communication_address_state",
            "communication_address_state_name",
            "communication_address_city",
            "communication_address_city_name",
            "communication_address_building",
            "communication_address_area",
            "communication_address_area_name",
            "communication_address_landmark",
            "communication_address_pincode",
            "created_by_name",
            "updated_by_name",
            "created_at",
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


class PartnerCompanyArchiveListSerializer(serializers.ModelSerializer):
    partner_company_logo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    gst_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    gst_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    gst_address_city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False, allow_null=True)
    gst_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )
    communication_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    communication_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    communication_address_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )
    communication_address_area = serializers.PrimaryKeyRelatedField(
        queryset=CityArea.objects.all(), required=False, allow_null=True
    )

    # Read-only fields for names
    gst_address_country_name = serializers.CharField(source="gst_address_country.name", read_only=True)
    gst_address_state_name = serializers.CharField(source="gst_address_state.name", read_only=True)
    gst_address_city_name = serializers.CharField(source="gst_address_city.name", read_only=True)
    gst_address_area_name = serializers.CharField(source="gst_address_area.city_area_name", read_only=True)
    communication_address_country_name = serializers.CharField(
        source="communication_address_country.name", read_only=True
    )
    communication_address_state_name = serializers.CharField(source="communication_address_state.name", read_only=True)
    communication_address_city_name = serializers.CharField(source="communication_address_city.name", read_only=True)
    communication_address_area_name = serializers.CharField(
        source="communication_address_area.city_area_name", read_only=True
    )

    class Meta:
        model = PartnerCompany
        fields = [
            "id",
            "partner_company_logo",
            "company_name",
            "person_name",
            "gst_no",
            "email",
            "phone",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_area",
            "gst_address_area_name",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_country_name",
            "communication_address_state",
            "communication_address_state_name",
            "communication_address_city",
            "communication_address_city_name",
            "communication_address_building",
            "communication_address_area",
            "communication_address_area_name",
            "communication_address_landmark",
            "communication_address_pincode",
            "is_active",
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


# Partner Company Multiple Deleted
class PartnerCompanyArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PartnerCompany
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        partner_company = []
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None

        for deleted_id in deleted_ids:
            try:
                partner_company_instance = PartnerCompany.objects.get(id=deleted_id)
                users = User.objects.filter(partner_company=partner_company_instance)

                if partner_company_instance.status == "pending":
                    partner_company_instance.deleted = True
                    partner_company_instance.status = "pending"
                    partner_company_instance.is_active = False

                    if hasattr(partner_company_instance, "deleted_by"):
                        partner_company_instance.deleted_by = user
                    if hasattr(partner_company_instance, "deleted_at"):
                        partner_company_instance.deleted_at = now()
                    partner_company_instance.save()
                else:
                    partner_company_instance.status = "inactive"
                    partner_company_instance.is_active = False
                    partner_company_instance.deleted = True

                    if hasattr(partner_company_instance, "deleted_by"):
                        partner_company_instance.deleted_by = user
                    if hasattr(partner_company_instance, "deleted_at"):
                        partner_company_instance.deleted_at = now()
                    partner_company_instance.save()

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
                    ActivityLog.log.partner_company_archive(partner_company_instance, users.first())
                partner_company.append(partner_company_instance)

            except PartnerCompany.DoesNotExist:
                raise serializers.ValidationError("Partner Company does not exist")

        return partner_company[-1] if partner_company else None


# Company Multiple Restore
class PartnerCompanyRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PartnerCompany
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        partner_company = []

        for deleted_id in deleted_ids:
            try:
                partner_company_instance = PartnerCompany.objects.get(id=deleted_id)
                users = User.objects.filter(partner_company=partner_company_instance)

                if partner_company_instance.status == "pending":
                    partner_company_instance.deleted = False
                    partner_company_instance.status = "pending"
                    partner_company_instance.is_active = False
                    partner_company_instance.deleted_by = None
                    partner_company_instance.deleted_at = None
                    partner_company_instance.updated_at = now()
                    partner_company_instance.save()
                else:
                    partner_company_instance.status = "active"
                    partner_company_instance.is_active = True
                    partner_company_instance.deleted = False
                    partner_company_instance.deleted_by = None
                    partner_company_instance.deleted_at = None
                    partner_company_instance.updated_at = now()
                    partner_company_instance.save()

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
                    ActivityLog.log.partner_company_restore(partner_company_instance, users.first())

                partner_company.append(partner_company_instance)

            except PartnerCompany.DoesNotExist:
                raise serializers.ValidationError("Partner Company does not exist")

        return partner_company[-1] if partner_company else None


class PartnerCompanyDocumentSerializer(serializers.ModelSerializer):
    partner_company_name = serializers.CharField(source="partner_company.company_name", required=False)
    document_title = serializers.CharField(required=False)
    document_file = serializers.CharField(required=False)

    class Meta:
        model = PartnerCompanyDocument
        fields = [
            "id",
            "partner_company",
            "partner_company_name",
            "document_title",
            "document_file",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


# Partner Company Document Multiple Archive
class PartnerCompanyDocumentArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PartnerCompanyDocument
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request")

        partner_company_id = request.query_params.get("partner_company_id") if request else None

        for deleted_id in deleted_ids:
            try:
                if partner_company_id:
                    partner_company_document = PartnerCompanyDocument.objects.get(
                        id=deleted_id, partner_company_id=partner_company_id
                    )
                elif request and request.user.partner_company:
                    partner_company_document = PartnerCompanyDocument.objects.get(
                        id=deleted_id, partner_company=request.user.partner_company
                    )
                else:
                    raise PartnerCompanyDocument.DoesNotExist()

                partner_company_document.deleted = True
                partner_company_document.save()
            except PartnerCompanyDocument.DoesNotExist:
                raise serializers.ValidationError("Partner Company Document does not exist or access denied")

        return partner_company_document


# Partner Company Document Archive/Restore Serializer
class PartnerCompanyDocumentRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PartnerCompanyDocument
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request")

        partner_company_id = request.query_params.get("partner_company_id") if request else None

        for deleted_id in deleted_ids:
            try:
                if partner_company_id:
                    partner_company_document = PartnerCompanyDocument.objects.get(
                        id=deleted_id, partner_company_id=partner_company_id
                    )
                elif request and request.user.partner_company:
                    partner_company_document = PartnerCompanyDocument.objects.get(
                        id=deleted_id, partner_company=request.user.partner_company
                    )
                else:
                    raise PartnerCompanyDocument.DoesNotExist()

                partner_company_document.deleted = False
                partner_company_document.deleted_by = None
                partner_company_document.deleted_at = None
                partner_company_document.updated_at = now()
                partner_company_document.save()
            except PartnerCompanyDocument.DoesNotExist:
                raise serializers.ValidationError("Partner Company Document does not exist or access denied")

        return partner_company_document
