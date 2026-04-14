from rest_framework import serializers

from city.models import City
from country.models import Country
from state.models import State
from user.models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    country = serializers.IntegerField(write_only=True)
    state = serializers.IntegerField(write_only=True)
    city = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "role",
            "country",
            "state",
            "city",
        ]

    def validate(self, data):
        role = data.get("role")
        country_id = data.pop("country", None)
        state_id = data.pop("state", None)
        city_id = data.pop("city", None)

        valid_roles = [
            "student",
            "parent",
            "working_professional",
            "college",
            "institute",
            "corporate",
        ]

        if role not in valid_roles:
            raise serializers.ValidationError("Invalid role selected")

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

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()

        return user
