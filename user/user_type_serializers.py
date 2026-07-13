import json

from django.db import transaction
from rest_framework import serializers

from city.models import City
from country.models import Country
from education_level.models import EducationLevel
from language_master.models import Language
from state.models import State
from stream.models import Stream
from user.models import User
from user.services.registration_service import setup_web_user_password
from user_profile.models import StudentProfile, ProfessionalProfile
from utils.auth import is_web_source, validate_password_strength


class RegisterSerializer(serializers.ModelSerializer):
    data = serializers.CharField(write_only=True, required=True)
    profile_image = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = User
        fields = ["data", "profile_image"]

    def validate(self, data):
        try:
            json_data = json.loads(data.get("data"))
        except json.JSONDecodeError:
            raise serializers.ValidationError({"data": "Invalid JSON format"})

        password = json_data.get("password")
        confirm_password = json_data.get("confirm_password")
        terms_accepted = json_data.get("terms_accepted")
        email = json_data.get("email")
        first_name = json_data.get("first_name")
        last_name = json_data.get("last_name")
        phone = json_data.get("phone")
        user_type = json_data.get("user_type")
        country_id = json_data.get("country")
        state_id = json_data.get("state")
        city_id = json_data.get("city")
        address = json_data.get("address")
        referral_code = (json_data.get("referral_code") or "").strip()
        source = json_data.get("source")
        is_web = is_web_source(source)
        errors = {}

        if not email:
            errors["email"] = "This field is required."
        if not is_web:
            if not password:
                errors["password"] = "This field is required."
            if not confirm_password:
                errors["confirm_password"] = "This field is required."
        if not first_name:
            errors["first_name"] = "This field is required."
        if not user_type:
            errors["user_type"] = "This field is required."
        if not country_id:
            errors["country"] = "This field is required."
        if not state_id:
            errors["state"] = "This field is required."
        if not city_id:
            errors["city"] = "This field is required."
        if terms_accepted is None:
            errors["terms_accepted"] = "This field is required."

        if errors:
            raise serializers.ValidationError(errors)

        if not is_web:
            errors.update(validate_password_strength(password))
            if password != confirm_password:
                errors["confirm_password"] = "Passwords do not match."

        if User.objects.filter(email=email, deleted=False).exists():
            errors["email"] = "An account with this email already exists."
        if phone and User.objects.filter(phone=phone, deleted=False).exists():
            errors["phone"] = "An account with this phone number already exists."

        if not terms_accepted:
            errors["terms_accepted"] = (
                "You must accept the Terms & Conditions to create an account."
            )

        country = Country.objects.filter(id=country_id).first()
        if not country:
            errors["country"] = "Invalid country id"
        state = State.objects.filter(id=state_id).first()
        if not state:
            errors["state"] = "Invalid state id"
        city = City.objects.filter(id=city_id).first()
        if not city:
            errors["city"] = "Invalid city id"

        valid_user_types = [r.value for r in User.Role]
        if user_type not in valid_user_types:
            errors["user_type"] = (
                f"Invalid user_type. Must be one of: {', '.join(valid_user_types)}"
            )

        referred_by = None
        if referral_code:
            if user_type == User.Role.STUDENT:
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

            elif user_type == User.Role.PROFESSIONAL:
                referred_by = User.objects.filter(
                    referral_code__iexact=referral_code,
                    user_type__in=[
                        User.Role.CORPORATE,
                    ],
                    deleted=False,
                ).first()
                if not referred_by:
                    errors["referral_code"] = "Invalid referral code."
        if errors:
            raise serializers.ValidationError(errors)

        validated_data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "phone": phone,
            "user_type": user_type,
            "country": country,
            "states": state,
            "city": city,
            "address": address or None,
            "password": password,
            "terms_accepted": terms_accepted,
            "source": source,
            "referred_by": referred_by,
        }
        if user_type in [
            User.Role.SCHOOL_COLLEGE,
            User.Role.INSTITUTE,
            User.Role.CORPORATE,
        ]:
            validated_data["referral_code"] = referral_code
        data["validated_data"] = validated_data

        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data_inner = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        password = validated_data_inner.pop("password", None)
        terms_accepted = validated_data_inner.pop("terms_accepted")
        source = validated_data_inner.pop("source", None)
        referred_by = validated_data_inner.pop("referred_by", None)

        user = User.objects.create(**validated_data_inner)
        user.created_by = user
        is_web = is_web_source(source)
        if is_web:
            setup_web_user_password(user)
        else:
            user.set_password(password)

        user.terms_accepted = terms_accepted
        if is_web:
            user.save(update_fields=["terms_accepted", "created_by"])
        else:
            user.save()

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        def update_profile_referral():
            if user.user_type == User.Role.STUDENT:
                profile = StudentProfile.objects.get(user=user)
                profile.referred_by = referred_by
                profile.save(update_fields=["referred_by"])

            elif user.user_type == User.Role.PROFESSIONAL:
                profile = ProfessionalProfile.objects.get(user=user)
                profile.referred_by = referred_by
                profile.save(update_fields=["referred_by"])

        if referred_by:
            transaction.on_commit(update_profile_referral)
        return user
