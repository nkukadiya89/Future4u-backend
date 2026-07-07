import json

from django.db import transaction
from rest_framework import serializers
from datetime import datetime
from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password
from email_utils.send_email import send_email_change_notification
from user_profile.models import InstituteProfile


class AdminInstituteSerializer(serializers.ModelSerializer):
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
        referral_code = (json_data.get("referral_code") or "").strip()

        institute_name = json_data.get("institute_name")
        student_trained = json_data.get("student_trained")
        placements = json_data.get("placements")
        about_us = json_data.get("about_us")
        courses_offered = json_data.get("courses_offered")
        website = json_data.get("website")

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

        if student_trained is not None and student_trained != "":
            if not isinstance(student_trained, int) or student_trained < 0:
                errors["student_trained"] = "Student trained must be a positive integer"

        if placements is not None and placements != "":
            if not isinstance(placements, int) or placements < 0:
                errors["placements"] = "Placements must be a positive integer"

        if courses_offered is not None and not isinstance(courses_offered, list):
            errors["courses_offered"] = "Courses offered must be a list"

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
        if "referral_code" in json_data:
            validated["referral_code"] = referral_code

        if "address" in json_data:
            validated["address"] = (address or "").strip() or None

        if "institute_name" in json_data:
            validated["institute_name"] = institute_name
        if "student_trained" in json_data:
            val = student_trained
            if isinstance(val, str) and val.strip() == "":
                val = None
            validated["student_trained"] = val
        if "placements" in json_data:
            val = placements
            if isinstance(val, str) and val.strip() == "":
                val = None
            validated["placements"] = val
        if "about_us" in json_data:
            validated["about_us"] = about_us
        if "courses_offered" in json_data:
            validated["courses_offered"] = courses_offered
        if "website" in json_data:
            validated["website"] = website

        data["validated_data"] = validated
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        institute_name = data.pop("institute_name", None)
        student_trained = data.pop("student_trained", None)
        placements = data.pop("placements", None)
        about_us = data.pop("about_us", None)
        courses_offered = data.pop("courses_offered", None)
        website = data.pop("website", None)

        user = User.objects.create(
            **data,
            user_type=User.Role.INSTITUTE,
            created_by=request.user,
            terms_accepted=True,
        )

        setup_web_user_password(user)

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        InstituteProfile.objects.create(
            user=user,
            institute_name=institute_name,
            student_trained=student_trained,
            placements=placements,
            about_us=about_us,
            courses_offered=courses_offered or [],
            website=website,
        )

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        old_email = instance.email

        institute_name_sent = "institute_name" in data
        institute_name = data.pop("institute_name", None)
        student_trained_sent = "student_trained" in data
        student_trained = data.pop("student_trained", None)
        placements_sent = "placements" in data
        placements = data.pop("placements", None)
        about_us_sent = "about_us" in data
        about_us = data.pop("about_us", None)
        courses_offered_sent = "courses_offered" in data
        courses_offered = data.pop("courses_offered", None)
        website_sent = "website" in data
        website = data.pop("website", None)

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save(user=request.user)

        if profile_image_file:
            instance.upload_profile_image(profile_image_file)

        try:
            profile = instance.institute_profile
        except InstituteProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"institute_profile": "Institute Profile not found"}
            )

        if institute_name_sent:
            profile.institute_name = institute_name
        if student_trained_sent:
            profile.student_trained = student_trained
        if placements_sent:
            profile.placements = placements
        if about_us_sent:
            profile.about_us = about_us
        if courses_offered_sent:
            profile.courses_offered = courses_offered
        if website_sent:
            profile.website = website
        profile.updated_by = request.user
        profile.updated_at = datetime.now()
        profile.save()

        email_changed = old_email.lower() != instance.email.lower()

        if email_changed:
            send_email_change_notification(
                old_email=old_email,
                new_email=instance.email,
                user=instance,
            )
            setup_web_user_password(instance)

        return instance
    
class AdminInstituteSortSerializer(serializers.ModelSerializer):
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
    referral_code = serializers.CharField(source="user.referral_code")
    address = serializers.CharField(source="user.address")
    
    class Meta:
        model = InstituteProfile
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
            "referral_code",
            "institute_name",
            "student_trained",
            "placements",
            "about_us",
            "courses_offered",
            "website",
        ]