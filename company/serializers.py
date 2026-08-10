from django.utils.timezone import now
from rest_framework import serializers

import company.serializer as company_serializer
from activity_log.models import ActivityLog
from city.models import City
from common.mixins.serializer_mixins import (
    DateFieldsMixin,
    DeletedFieldsMixin,
    UserNameMixin,
)
from company.models import Company, CompanyPhoto, CompanyService, Enquiry
from country.models import Country
from state.models import State
from user.models import CustomGroup, User
from utils.generate_ip_address import get_client_ip
from utils.generate_random_password import generate_random_password
from utils.role_permission import create_company_role_family


class CreateCompanySerializer(serializers.ModelSerializer):
    phone = serializers.IntegerField()
    business_category_name = serializers.CharField(
        source="business_category.business_category", required=False
    )
    gst_address_country = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True
    )
    gst_address_state = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True
    )
    gst_address_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
    )

    # Read-only fields for names
    gst_address_country_name = serializers.CharField(
        source="gst_address_country.name", read_only=True
    )
    gst_address_state_name = serializers.CharField(
        source="gst_address_state.name", read_only=True
    )
    gst_address_city_name = serializers.CharField(
        source="gst_address_city.name", read_only=True
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "gst_no",
            "name",
            "business_category",
            "business_category_name",
            "person_name",
            "email",
            "phone",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_landmark",
            "gst_address_pincode",
            "status",
            "is_active",
            "is_request_demo",
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
            "first_name": validated_data["person_name"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        user = User.objects.create(**user_data)
        user.set_password(password)
        company_instance = Company.objects.create(**validated_data)
        # Owner link: company is associated with its admin user (this flow is
        # the public self-registration, so request.user is anonymous).
        company_instance.created_by = user
        company_instance.save()
        company_id = company_instance.id
        result = create_company_role_family(req, company_id)
        if result["success"]:
            for group in result["company_group"]:
                group.user_set.add(user)
        else:
            raise serializers.ValidationError(
                {"success": False, "message": result["message"]}
            )

        try:
            company_admin_group = CustomGroup.objects.get(name="Company Admin")
            company_admin_group.user_set.add(user)
            user.designation = (
                company_admin_group.group_name
                if company_admin_group.group_name
                else company_admin_group.name
            )
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": "Company Admin group not found"}
            )

        ActivityLog.log.company_create(company_instance, ip_address, user)
        user.save()

        return company_instance


class CompanyPhotoSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    photo_file = serializers.CharField(required=False)

    class Meta:
        model = CompanyPhoto
        fields = [
            "id",
            "company",
            "company_name",
            "title",
            "photo_file",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }


class CompanyPhotoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPhoto
        fields = [
            "id",
            "title",
            "photo_file",
        ]


class CompanyPhotosMixin:
    def get_company_photos(self, obj):
        photos = obj.company_photo.filter(deleted=False)
        return CompanyPhotoListSerializer(photos, many=True).data


class CompanyPhotoArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CompanyPhoto
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request")

        company_id = request.query_params.get("company_id") if request else None

        for deleted_id in deleted_ids:
            try:
                if company_id:
                    company_photo = CompanyPhoto.objects.get(
                        id=deleted_id, company_id=company_id
                    )
                elif request and request.user.company:
                    company_photo = CompanyPhoto.objects.get(
                        id=deleted_id, company=request.user.company
                    )
                else:
                    raise CompanyPhoto.DoesNotExist()

                company_photo.deleted = True
                company_photo.save()
            except CompanyPhoto.DoesNotExist:
                raise serializers.ValidationError(
                    "Company Photo does not exist or access denied"
                )

        return company_photo


class CompanyPhotoRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CompanyPhoto
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request")

        company_id = request.query_params.get("company_id") if request else None

        for deleted_id in deleted_ids:
            try:
                if company_id:
                    company_photo = CompanyPhoto.objects.get(
                        id=deleted_id, company_id=company_id
                    )
                elif request and request.user.company:
                    company_photo = CompanyPhoto.objects.get(
                        id=deleted_id, company=request.user.company
                    )
                else:
                    raise CompanyPhoto.DoesNotExist()

                company_photo.deleted = False
                company_photo.deleted_by = None
                company_photo.deleted_at = None
                company_photo.updated_at = now()
                company_photo.save()
            except CompanyPhoto.DoesNotExist:
                raise serializers.ValidationError(
                    "Company Photo does not exist or access denied"
                )

        return company_photo


class CompanyServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyService
        fields = ["id", "name"]
        read_only_fields = ["id", "name"]


class CompanySerializer(
    CompanyPhotosMixin,
    DateFieldsMixin,
    UserNameMixin,
    serializers.ModelSerializer,
):
    phone = serializers.IntegerField()
    company_name = serializers.CharField(source="name", read_only=True)
    business_category_name = serializers.CharField(
        source="business_category.business_category", required=False
    )
    services_list = CompanyServiceSerializer(
        many=True, source="services", read_only=True
    )
    services = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField(allow_blank=True)),
        write_only=True,
        required=False,
        allow_empty=True,
    )
    company_photos = serializers.SerializerMethodField()
    company_logo = serializers.CharField(required=False)
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
    gst_address_city = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(), required=False, allow_null=True
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

    # Read-only fields for names
    gst_address_country_name = serializers.CharField(
        source="gst_address_country.name", read_only=True
    )
    gst_address_state_name = serializers.CharField(
        source="gst_address_state.name", read_only=True
    )
    gst_address_city_name = serializers.CharField(
        source="gst_address_city.name", read_only=True
    )
    communication_address_country_name = serializers.CharField(
        source="communication_address_country.name", read_only=True
    )
    communication_address_state_name = serializers.CharField(
        source="communication_address_state.name", read_only=True
    )
    communication_address_city_name = serializers.CharField(
        source="communication_address_city.name", read_only=True
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "company_logo",
            "gst_no",
            "gst_no_verified",
            "company_name",
            "name",
            "business_category",
            "business_category_name",
            "person_name",
            "email",
            "phone",
            "company_type",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_country_name",
            "communication_address_state",
            "communication_address_state_name",
            "communication_address_city",
            "communication_address_city_name",
            "communication_address_building",
            "communication_address_landmark",
            "communication_address_pincode",
            "status",
            "is_active",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "secondary_email",
            "secondary_phone",
            "facebook_url",
            "twitter_url",
            "linkedin_url",
            "instagram_url",
            "youtube_url",
            "pinterest_url",
            "year_of_establishment",
            "number_of_employees",
            "monday_friday_hours",
            "saturday_hours",
            "sunday_hours",
            "services_list",
            "services",
            "company_photos",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
            "business_category": {"required": False, "allow_null": True},
        }

    def validate(self, data):
        errors = {}
        name = data.get("name")
        if self.instance and self.instance.name == name:
            return data
        if Company.objects.filter(name=name).exists():
            errors["name"] = f"Company with this Name {name} already exists."

        email = data.get("email")
        if self.instance and self.instance.email == email:
            return data
        if Company.objects.filter(email=email).exists():
            errors["email"] = f"Company with this Email {email} already exists."

        phone = data.get("phone")
        if self.instance and self.instance.phone == phone:
            return data
        if Company.objects.filter(phone=phone).exists():
            errors["phone"] = f"Company with this Phone {phone} already exists."

        email = data.get("email", None)
        if email is not None:
            pc_qs = Company.objects.filter(email=email)
            if self.instance:
                pc_qs = pc_qs.exclude(pk=self.instance.pk)
            email_changed = not (self.instance and self.instance.email == email)
            if pc_qs.exists() or (
                email_changed and User.objects.filter(email=email).exists()
            ):
                errors["email"] = (
                    f"Partner Company with this Email {email} already exists."
                )

        phone = data.get("phone", None)
        if phone is not None and self.instance is None:
            pc_qs = Company.objects.filter(phone=phone)
            if pc_qs.exists() or User.objects.filter(phone=phone).exists():
                errors["phone"] = (
                    f"Partner Company with this Phone {phone} already exists."
                )

        gst_no = data.get("gst_no")
        if gst_no and self.instance and self.instance.gst_no == gst_no:
            return data
        if gst_no and Company.objects.filter(gst_no=gst_no).exists():
            errors["gst_no"] = f"Company with this GST Number {gst_no} already exists."

        return data

    def create(self, validated_data):
        req = self.context.get("request")
        ip_address = get_client_ip(req)
        password = validated_data.pop("password", None)

        if not password:
            password = generate_random_password(self)

        services_data = validated_data.pop("services", [])

        phone = str(validated_data.get("phone", "")).strip()
        if not phone.isdigit():
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": "Please enter a valid mobile number.",
                }
            )

        user_data = {
            "first_name": validated_data["person_name"],
            "email": validated_data["email"],
            "phone": validated_data["phone"],
            "status": "pending",
        }

        try:
            user = User.objects.get(email=user_data["email"])
            raise serializers.ValidationError(
                {
                    "success": False,
                    "message": f"Company with this Email {user_data['email']} already exists.",
                }
            )
        except User.DoesNotExist:
            user = User.objects.create(**user_data)

        user.set_password(password)
        company_instance = Company.objects.create(**validated_data)
        company_instance.created_by = req.user
        company_instance.save()
        company_id = company_instance.id
        result = create_company_role_family(req, company_id)
        if result["success"]:
            for group in result["company_group"]:
                group.user_set.add(user)
        else:
            raise serializers.ValidationError(
                {"success": False, "message": result["message"]}
            )

        try:
            company_admin_group = CustomGroup.objects.get(name="Company Admin")
            company_admin_group.user_set.add(user)
            user.designation = (
                company_admin_group.group_name
                if company_admin_group.group_name
                else company_admin_group.name
            )
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError(
                {"success": False, "message": "Company Admin group not found"}
            )

        for service_data in services_data:
            service_name = service_data["name"]
            service = CompanyService.objects.filter(name=service_name).first()
            if not service:
                service = CompanyService.objects.create(name=service_name)
            company_instance.services.add(service)

        ActivityLog.log.company_create(company_instance, ip_address, user)
        user.save()

        return company_instance

    def update(self, instance, validated_data):
        request = self.context.get("request")
        ip_address = get_client_ip(request)

        phone = str(validated_data.get("phone", instance.phone or "")).strip()
        if phone and not phone.isdigit():
            raise serializers.ValidationError(
                {"phone": "Please enter a valid mobile number."}
            )

        services_data = validated_data.pop("services", [])
        incoming_service_ids = set()

        old_email = instance.email
        old_phone = instance.phone

        for service_item in services_data:
            service_id = service_item.get("id")
            service_name = service_item.get("name", "").strip()

            if not service_name:
                raise serializers.ValidationError(
                    {"services": "Service name cannot be empty."}
                )

            if service_id:
                try:
                    service = CompanyService.objects.get(id=service_id)
                    incoming_service_ids.add(service_id)

                    if service.name.lower() != service_name.lower():
                        service.name = service_name
                        service.updated_at = now()
                        service.save()

                except CompanyService.DoesNotExist:
                    raise serializers.ValidationError(
                        {"services": f"Service with id {service_id} does not exist."}
                    )

            else:
                new_service = CompanyService.objects.create(name=service_name)
                instance.services.add(new_service)
                incoming_service_ids.add(new_service.id)

        instance.name = validated_data.get("name", instance.name)
        instance.person_name = validated_data.get("person_name", instance.person_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone = validated_data.get("phone", instance.phone)
        instance.gst_no = validated_data.get("gst_no", instance.gst_no)
        instance.gst_no_verified = validated_data.get(
            "gst_no_verified", instance.gst_no_verified
        )
        instance.business_category = validated_data.get(
            "business_category", instance.business_category
        )
        instance.company_type = validated_data.get(
            "company_type", instance.company_type
        )
        instance.status = validated_data.get("status", instance.status)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.company_logo = validated_data.get(
            "company_logo", instance.company_logo
        )
        instance.gst_address_country = validated_data.get(
            "gst_address_country", instance.gst_address_country
        )
        instance.gst_address_state = validated_data.get(
            "gst_address_state", instance.gst_address_state
        )
        instance.gst_address_city = validated_data.get(
            "gst_address_city", instance.gst_address_city
        )
        instance.gst_address_building = validated_data.get(
            "gst_address_building", instance.gst_address_building
        )
        instance.gst_address_landmark = validated_data.get(
            "gst_address_landmark", instance.gst_address_landmark
        )
        instance.gst_address_pincode = validated_data.get(
            "gst_address_pincode", instance.gst_address_pincode
        )
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
        instance.communication_address_landmark = validated_data.get(
            "communication_address_landmark", instance.communication_address_landmark
        )
        instance.communication_address_pincode = validated_data.get(
            "communication_address_pincode", instance.communication_address_pincode
        )

        instance.secondary_email = validated_data.get(
            "secondary_email", instance.secondary_email
        )
        instance.secondary_phone = validated_data.get(
            "secondary_phone", instance.secondary_phone
        )
        instance.facebook_url = validated_data.get(
            "facebook_url", instance.facebook_url
        )
        instance.twitter_url = validated_data.get("twitter_url", instance.twitter_url)
        instance.linkedin_url = validated_data.get(
            "linkedin_url", instance.linkedin_url
        )
        instance.instagram_url = validated_data.get(
            "instagram_url", instance.instagram_url
        )
        instance.youtube_url = validated_data.get("youtube_url", instance.youtube_url)
        instance.pinterest_url = validated_data.get(
            "pinterest_url", instance.pinterest_url
        )
        instance.year_of_establishment = validated_data.get(
            "year_of_establishment", instance.year_of_establishment
        )
        instance.number_of_employees = validated_data.get(
            "number_of_employees", instance.number_of_employees
        )
        instance.monday_friday_hours = validated_data.get(
            "monday_friday_hours", instance.monday_friday_hours
        )
        instance.saturday_hours = validated_data.get(
            "saturday_hours", instance.saturday_hours
        )
        instance.sunday_hours = validated_data.get(
            "sunday_hours", instance.sunday_hours
        )

        instance.updated_by = request.user
        instance.updated_at = now()

        instance.save()

        users = User.objects.filter(groups__customgroup__company=instance)
        for user in users:
            if "person_name" in validated_data:
                user.first_name = validated_data["person_name"]
            if "email" in validated_data and user.email == old_email:
                user.email = validated_data["email"]
            if "phone" in validated_data and user.phone == old_phone:
                user.phone = validated_data["phone"]

            user.save()

        ActivityLog.log.company_update(instance, ip_address, request.user)

        return instance


class CompanyInfoSerializer(
    CompanyPhotosMixin,
    DateFieldsMixin,
    UserNameMixin,
    serializers.ModelSerializer,
):
    business_category_name = serializers.CharField(
        source="business_category.business_category", required=False
    )
    company_logo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    services = CompanyServiceSerializer(many=True, read_only=True)
    company_photos = serializers.SerializerMethodField()

    gst_address_country_name = serializers.CharField(
        source="gst_address_country.name", read_only=True
    )
    gst_address_state_name = serializers.CharField(
        source="gst_address_state.name", read_only=True
    )
    gst_address_city_name = serializers.CharField(
        source="gst_address_city.name", read_only=True
    )
    communication_address_country_name = serializers.CharField(
        source="communication_address_country.name", read_only=True
    )
    communication_address_state_name = serializers.CharField(
        source="communication_address_state.name", read_only=True
    )
    communication_address_city_name = serializers.CharField(
        source="communication_address_city.name", read_only=True
    )

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "person_name",
            "gst_no",
            "gst_no_verified",
            "business_category",
            "business_category_name",
            "email",
            "phone",
            "company_type",
            "status",
            "is_active",
            "company_logo",
            "gst_address_country",
            "gst_address_country_name",
            "gst_address_state",
            "gst_address_state_name",
            "gst_address_city",
            "gst_address_city_name",
            "gst_address_building",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_country_name",
            "communication_address_state",
            "communication_address_state_name",
            "communication_address_city",
            "communication_address_city_name",
            "communication_address_building",
            "communication_address_landmark",
            "communication_address_pincode",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "secondary_email",
            "secondary_phone",
            "facebook_url",
            "twitter_url",
            "linkedin_url",
            "instagram_url",
            "youtube_url",
            "pinterest_url",
            "year_of_establishment",
            "number_of_employees",
            "monday_friday_hours",
            "saturday_hours",
            "sunday_hours",
            "services",
            "company_photos",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        return ret


class CompanyArchiveListSerializer(
    DateFieldsMixin,
    UserNameMixin,
    DeletedFieldsMixin,
    serializers.ModelSerializer,
):
    business_category_name = serializers.CharField(
        source="business_category.business_category", required=False
    )
    company_logo = serializers.CharField(required=False)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "company_logo",
            "name",
            "person_name",
            "gst_no",
            "business_category",
            "business_category_name",
            "email",
            "phone",
            "company_type",
            "gst_address_country",
            "gst_address_state",
            "gst_address_city",
            "gst_address_building",
            "gst_address_landmark",
            "gst_address_pincode",
            "communication_address_country",
            "communication_address_state",
            "communication_address_city",
            "communication_address_building",
            "communication_address_landmark",
            "communication_address_pincode",
            "status",
            "is_active",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
            "deleted",
        ]


class CompanyArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Company
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        companies = []
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        ip_address = get_client_ip(request)

        for deleted_id in deleted_ids:
            try:
                users = User.objects.filter(groups__customgroup__company_id=deleted_id)

                company = Company.objects.get(id=deleted_id)

                if company.status == "pending":
                    company.deleted = True
                    company.status = "pending"
                    company.is_active = False
                    if hasattr(company, "deleted_by"):
                        company.deleted_by = user
                    if hasattr(company, "deleted_at"):
                        company.deleted_at = now()
                    company.save()
                else:
                    company.status = "inactive"
                    company.is_active = False
                    company.deleted = True
                    if hasattr(company, "deleted_by"):
                        company.deleted_by = user
                    if hasattr(company, "deleted_at"):
                        company.deleted_at = now()
                    company.save()

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

                ActivityLog.log.company_archive(company, ip_address, users.first())
                companies.append(company)

            except Company.DoesNotExist:
                raise serializers.ValidationError("Company does not exist")

        return companies[-1] if companies else None


class CompanyRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Company
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        companies = []
        req = self.context.get("request")
        ip_address = get_client_ip(req)

        for deleted_id in deleted_ids:
            try:
                company = Company.objects.get(id=deleted_id)
                users = User.objects.filter(groups__customgroup__company=company)

                if company.status == "pending":
                    company.status = "pending"
                    company.is_active = False
                    company.deleted = False
                    company.deleted_by = None
                    company.deleted_at = None
                    company.updated_at = now()
                    company.save()
                else:
                    company.status = "active"
                    company.is_active = True
                    company.deleted = False
                    company.deleted_by = None
                    company.deleted_at = None
                    company.updated_at = now()
                    company.save()

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

                ActivityLog.log.company_restore(company, ip_address, users.first())

                companies.append(company)

            except Company.DoesNotExist:
                raise serializers.ValidationError("Company does not exist")

        return companies[-1] if companies else None


class EnquirySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(
        source="user.get_full_name", read_only=True, allow_null=True
    )
    send_enquiry_to_name = serializers.CharField(
        source="send_enquiry_to.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Enquiry
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "message",
            "user",
            "user_name",
            "send_enquiry_to",
            "send_enquiry_to_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "user_name",
            "send_enquiry_to_name",
            "created_at",
        ]
