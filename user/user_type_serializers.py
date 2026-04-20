import json
import re

from django.db import transaction
from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user_profile.models import UserProfile


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

        # Extract fields from JSON
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

        # Validate required fields
        errors = {}
        if not email:
            errors["email"] = "This field is required."
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

        # Validate password
        if not re.search(r"[A-Z]", password):
            errors["password"] = "Password must contain at least 1 uppercase letter."
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors["password"] = "Password must contain at least 1 special character."
        if not re.search(r"[0-9]", password):
            errors["password"] = "Password must contain at least 1 number."
        if len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."

        # Validate password match
        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        # Validate email uniqueness
        if User.objects.filter(email=email).exists():
            errors["email"] = "An account with this email already exists."

        # Validate terms accepted
        if not terms_accepted:
            errors["terms_accepted"] = "You must accept the Terms & Conditions to create an account."

        # Validate country, state, city
        country = Country.objects.filter(id=country_id).first()
        if not country:
            errors["country"] = "Invalid country id"
        state = State.objects.filter(id=state_id).first()
        if not state:
            errors["state"] = "Invalid state id"
        city = City.objects.filter(id=city_id).first()
        if not city:
            errors["city"] = "Invalid city id"

        # Validate user_type
        valid_user_types = [r.value for r in User.Role]
        if user_type not in valid_user_types:
            errors["user_type"] = f"Invalid user_type. Must be one of: {', '.join(valid_user_types)}"

        if errors:
            raise serializers.ValidationError(errors)

        # Return validated data
        data["validated_data"] = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name or "",
            "phone": phone,
            "user_type": user_type,
            "country": country,
            "states": state,
            "city": city,
            "password": password,
            "terms_accepted": terms_accepted,
        }
        data["profile_image_file"] = data.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        validated_data_inner = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image")

        password = validated_data_inner.pop("password")
        terms_accepted = validated_data_inner.pop("terms_accepted")

        user = User.objects.create(**validated_data_inner)
        user.set_password(password)
        user.is_active = True  # TODO: set to False when email verification is enabled
        user.terms_accepted = terms_accepted
        user.save()

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        return user
