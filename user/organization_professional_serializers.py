import json

from django.db import transaction
from rest_framework import serializers

from city.models import City
from common.serializers import BaseModelSerializer
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password
from user_profile.models import ProfessionalProfile


class OrganizationProfessionalCreateSerializer(BaseModelSerializer):
    data = serializers.CharField(write_only=True, required=True)
    profile_image = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["data", "profile_image"]

    def validate(self, data):
        raw_data = data.get("data") or "{}"
        try:
            json_data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise serializers.ValidationError({"data": "Invalid JSON format"})

        email = (json_data.get("email") or "").strip().lower()
        first_name = (json_data.get("first_name") or "").strip()
        last_name = (json_data.get("last_name") or "").strip()
        phone = (json_data.get("phone") or "").strip()
        address = (json_data.get("address") or "").strip()

        country_id = json_data.get("country")
        state_id = json_data.get("state")
        city_id = json_data.get("city")

        errors = {}

        if not email:
            errors["email"] = "This field is required."

        if not first_name:
            errors["first_name"] = "This field is required."

        if not country_id:
            errors["country"] = "This field is required."

        if not state_id:
            errors["state"] = "This field is required."

        if not city_id:
            errors["city"] = "This field is required."

        if email and User.objects.filter(email__iexact=email, deleted=False).exists():
            errors["email"] = "An account with this email already exists."

        if phone and User.objects.filter(phone=phone, deleted=False).exists():
            errors["phone"] = "An account with this phone number already exists."

        country = None
        state = None
        city = None

        if country_id:
            country = Country.objects.filter(id=country_id, deleted=False).first()
            if not country:
                errors["country"] = "Invalid country id"
        if state_id:
            state = State.objects.filter(id=state_id, deleted=False).first()
            if not state:
                errors["state"] = "Invalid state id"

        if city_id:
            city = City.objects.filter(id=city_id, deleted=False).first()
            if not city:
                errors["city"] = "Invalid city id"

        if errors:
            raise serializers.ValidationError(errors)

        validated_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "phone": phone or None,
            "country": country,
            "states": state,
            "city": city,
            "address": address or None,
        }

        data["validated_data"] = validated_data
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")

        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        creator = request.user

        validated_data_inner = validated_data.get("validated_data", {})

        profile_image_file = validated_data.get("profile_image_file")

        professional = User.objects.create(
            **validated_data_inner,
            user_type=User.Role.PROFESSIONAL,
            created_by=creator,
            terms_accepted=True,
            status="pending",
            is_active=False,
            email_verified=False,
            must_change_password=True,
        )
        setup_web_user_password(professional)

        professional.created_by = creator
        professional.save(update_fields=["created_by"])

        ProfessionalProfile.objects.create(user=professional)
        if profile_image_file:
            professional.upload_profile_image(profile_image_file)

        return professional


class OrganizationProfessionalListSerializer(BaseModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    states_name = serializers.CharField(source="states.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    education_level = serializers.CharField(
        source="professional_profile.education_level.display_name",
        read_only=True,
        default=None,
    )
    employment_type = serializers.CharField(
        source="professional_profile.employment_type",
        read_only=True,
        default=None,
    )
    years_of_experience = serializers.CharField(
        source="professional_profile.years_of_experience",
        read_only=True,
        default=None,
    )
    current_job_title = serializers.CharField(
        source="professional_profile.current_job_title",
        read_only=True,
        default=None,
    )
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "first_name",
            "last_name",
            "user_type",
            "education_level",
            "employment_type",
            "years_of_experience",
            "current_job_title",
            "last_active",
            "email",
            "email_verified",
            "must_change_password",
            "phone",
            "address",
            "country",
            "country_name",
            "states",
            "states_name",
            "city",
            "city_name",
            "profile_image",
            "is_active",
            "status",
        ]
        read_only_fields = fields

    def get_last_active(self, obj):
        return obj.last_login.date().isoformat() if obj.last_login else None
