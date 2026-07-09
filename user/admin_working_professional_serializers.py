from datetime import datetime
import json
from django.db import transaction
from rest_framework import serializers
from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password
from email_utils.send_email import send_email_change_notification
from user_profile.models import ProfessionalProfile


class AdminWorkingProfessionalSerializer(serializers.ModelSerializer):
    data = serializers.CharField(write_only=True, required=False)
    profile_image = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["data", "profile_image"]

    def validate(self, data):
        raw_data = data.get("data") or "{}"
        try:
            json_data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise serializers.ValidationError({"data": "Invalid JSON format"})

        errors = {}
        is_update = self.instance is not None

        email = json_data.get("email")
        first_name = json_data.get("first_name")
        last_name = json_data.get("last_name")
        phone = json_data.get("phone")
        country_id = json_data.get("country")
        state_id = json_data.get("state")
        city_id = json_data.get("city")
        address = json_data.get("address")
        years_of_experience = json_data.get("years_of_experience")
        employment_type = json_data.get("employment_type")
        referral_code = (json_data.get("referral_code") or "").strip()

        if not is_update:
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

        if email and User.objects.filter(email=email, deleted=False).exclude(
            id=getattr(self.instance, "id", None)
        ).exists():
            errors["email"] = "An account with this email already exists"

        if phone and User.objects.filter(phone=phone, deleted=False).exclude(
            id=getattr(self.instance, "id", None)
        ).exists():
            errors["phone"] = "An account with this phone number already exists"

        country = None
        if country_id is not None:
            country = Country.objects.filter(id=country_id).first()
            if not country:
                errors["country"] = "Invalid country id"

        state = None
        if state_id is not None:
            state = State.objects.filter(id=state_id).first()
            if not state:
                errors["state"] = "Invalid state id"

        city = None
        if city_id is not None:
            city = City.objects.filter(id=city_id).first()
            if not city:
                errors["city"] = "Invalid city id"

        if years_of_experience is not None:
            valid_choices = [
                choice[0]
                for choice in ProfessionalProfile._meta.get_field("years_of_experience").choices
            ]
            if years_of_experience not in valid_choices:
                errors["years_of_experience"] = "Invalid years_of_experience value"

        if employment_type is not None:
            valid_choices = [
                choice[0]
                for choice in ProfessionalProfile._meta.get_field("employment_type").choices
            ]
            if employment_type not in valid_choices:
                errors["employment_type"] = "Invalid employment_type value"

        referred_by = None
        if referral_code:
            referred_by = User.objects.filter(
                referral_code__iexact=referral_code,
                user_type__in=[
                    User.Role.SCHOOL_COLLEGE,
                    User.Role.INSTITUTE,
                    User.Role.CORPORATE,
                ],
                deleted=False,
            ).first()
            if not referred_by:
                errors["referral_code"] = "Invalid referral code."

        if errors:
            raise serializers.ValidationError(errors)

        validated = {}

        if email is not None:
            validated["email"] = email
        if first_name is not None:
            validated["first_name"] = first_name
        if last_name is not None:
            validated["last_name"] = last_name
        if phone is not None:
            validated["phone"] = phone
        if country_id is not None:
            validated["country"] = country
        if state_id is not None:
            validated["states"] = state
        if city_id is not None:
            validated["city"] = city
        if "address" in json_data:
            validated["address"] = (address or "").strip() or None
        if "years_of_experience" in json_data:
            validated["years_of_experience"] = years_of_experience
        if "employment_type" in json_data:
            validated["employment_type"] = employment_type
        if "referral_code" in json_data:
            validated["referred_by"] = referred_by

        data["validated_data"] = validated
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        years_of_experience = data.pop("years_of_experience", None)
        employment_type = data.pop("employment_type", None)
        referred_by = data.pop("referred_by", None)

        user = User.objects.create(
            **data,
            user_type=User.Role.PROFESSIONAL,
            created_by=request.user,
            terms_accepted=True,
        )
        setup_web_user_password(user)

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        ProfessionalProfile.objects.create(
            user=user,
            years_of_experience=years_of_experience,
            employment_type=employment_type,
            referred_by=referred_by,
        )

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        old_email = instance.email

        years_of_experience_sent = "years_of_experience" in data
        years_of_experience = data.pop("years_of_experience", None)
        employment_type_sent = "employment_type" in data
        employment_type = data.pop("employment_type", None)
        referral_sent = "referred_by" in data
        referred_by = data.pop("referred_by", None)

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save(user=request.user)

        if profile_image_file:
            instance.upload_profile_image(profile_image_file)

        try:
            profile = instance.professional_profile
        except ProfessionalProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"professional_profile": "Working Professional Profile not found"}
            )

        if years_of_experience_sent:
            profile.years_of_experience = years_of_experience
        if employment_type_sent:
            profile.employment_type = employment_type
        if referral_sent:
            profile.referred_by = referred_by

        profile.updated_by = request.user
        profile.updated_at = datetime.now()
        profile.save()

        if old_email.lower() != instance.email.lower():
            send_email_change_notification(
                old_email=old_email,
                new_email=instance.email,
                user=instance,
            )
            setup_web_user_password(instance)

        return instance


class AdminWorkingProfessionalSortSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    phone = serializers.CharField(source="user.phone")
    email = serializers.CharField(source="user.email")
    country = serializers.IntegerField(source="user.country.id", default=None)
    country_name = serializers.CharField(source="user.country.name")
    state = serializers.IntegerField(source="user.states.id", default=None)
    state_name = serializers.CharField(source="user.states.name")
    city = serializers.IntegerField(source="user.city.id", default=None)
    city_name = serializers.CharField(source="user.city.name")
    address = serializers.CharField(source="user.address")

    class Meta:
        model = ProfessionalProfile
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "phone",
            "email",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "address",
            "years_of_experience",
            "employment_type",
        ]
