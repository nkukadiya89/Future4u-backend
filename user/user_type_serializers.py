import json

from django.db import transaction
from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import activate_web_user_with_temporary_password
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

        if User.objects.filter(email=email).exists():
            errors["email"] = "An account with this email already exists."
        if phone and User.objects.filter(phone=phone).exists():
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

        if errors:
            raise serializers.ValidationError(errors)

        data["validated_data"] = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "phone": phone,
            "user_type": user_type,
            "country": country,
            "states": state,
            "city": city,
            "referral_code": referral_code,
            "password": password,
            "terms_accepted": terms_accepted,
            "source": source,
        }
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data_inner = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        password = validated_data_inner.pop("password", None)
        terms_accepted = validated_data_inner.pop("terms_accepted")
        source = validated_data_inner.pop("source", None)

        user = User.objects.create(**validated_data_inner)
        is_web = is_web_source(source)
        if is_web:
            activate_web_user_with_temporary_password(user)
        else:
            user.set_password(password)

        user.terms_accepted = terms_accepted
        if is_web:
            user.save(update_fields=["terms_accepted"])
        else:
            user.save()

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        return user

class AdminCreateUserSerializer(serializers.ModelSerializer):
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

        terms_accepted = json_data.get("terms_accepted")
        email = json_data.get("email")
        first_name = json_data.get("first_name")
        last_name = json_data.get("last_name")
        phone = json_data.get("phone")
        user_type = json_data.get("user_type")
        country_id = json_data.get("country")
        state_id = json_data.get("state")
        city_id = json_data.get("city")
        referral_code = (json_data.get("referral_code") or "").strip()
        errors = {}

        if not email:
            errors["email"] = "This field is required."
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

        if User.objects.filter(email=email).exists():
            errors["email"] = "An account with this email already exists."
        if phone and User.objects.filter(phone=phone).exists():
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

        request = self.context.get("request")
        if (
            user_type == User.Role.SUPER_ADMIN
            and request
            and not request.user.is_superuser
        ):
            errors["user_type"] = "Only a superuser can create super_admin accounts."

        if errors:
            raise serializers.ValidationError(errors)

        data["validated_data"] = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "phone": phone,
            "user_type": user_type,
            "country": country,
            "states": state,
            "city": city,
            "referral_code": referral_code,
            "terms_accepted": terms_accepted,
        }
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        validated_data_inner = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        terms_accepted = validated_data_inner.pop("terms_accepted")
        validated_data_inner["created_by"] = request.user

        user = User.objects.create(**validated_data_inner)
        activate_web_user_with_temporary_password(user)

        user.terms_accepted = terms_accepted
        user.save(update_fields=["terms_accepted"])

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        return user

class BulkUserUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        allowed_extensions = [".csv", ".xlsx"]

        filename = value.name.lower()

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                "Only CSV and XLSX files are allowed."
            )

        return value