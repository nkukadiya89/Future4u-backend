import re

from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user_profile.models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    terms_accepted = serializers.BooleanField(write_only=True)
    user_type = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in User.Role],
        required=True,
    )
    country = serializers.IntegerField(write_only=True)
    state = serializers.IntegerField(write_only=True)
    city = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "confirm_password",
            "terms_accepted",
            "first_name",
            "last_name",
            "phone",
            "user_type",
            "country",
            "state",
            "city",
        ]

    def validate_password(self, value):
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain at least 1 uppercase letter."
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError(
                "Password must contain at least 1 special character."
            )
        if not re.search(r"[0-9]", value):
            raise serializers.ValidationError(
                "Password must contain at least 1 number."
            )
        return value

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must accept the Terms & Conditions to create an account."
            )
        return value

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError(
                "You must accept the Terms & Conditions to create an account."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate(self, data):
        if data.get("password") != data.get("confirm_password"):
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        country_id = data.pop("country", None)
        state_id = data.pop("state", None)
        city_id = data.pop("city", None)
        data.pop("confirm_password", None)

        errors = {}
        country = Country.objects.filter(id=country_id).first()
        if not country:
            errors["country"] = "Invalid country id"
        state = State.objects.filter(id=state_id).first()
        if not state:
            errors["state"] = "Invalid state id"
        city = City.objects.filter(id=city_id).first()
        if not city:
            errors["city"] = "Invalid city id"
        if errors:
            raise serializers.ValidationError(errors)

        data["country"] = country
        data["states"] = state
        data["city"] = city
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        terms_accepted = validated_data.pop("terms_accepted", False)

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.terms_accepted = terms_accepted
        user.save()

        return user
