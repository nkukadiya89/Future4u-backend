import json

from rest_framework import serializers
from city.models import City
from country.models import Country
from education_level.models import EducationLevel
from email_utils.send_email import send_email_change_notification
from language_master.models import Language
from state.models import State
from stream.models import Stream
from user.models import User
from user.services.registration_service import setup_web_user_password
from user_profile.models import StudentProfile
from django.db import transaction
from datetime import datetime


class AdminStudentSerializer(serializers.ModelSerializer):
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
        education_level_id = json_data.get("education_level")
        stream_id = json_data.get("stream")
        language_ids = json_data.get("language", [])
        medium = json_data.get("medium")
        referral_code = (json_data.get("referral_code") or "").strip()

        language_sent = "language" in json_data
        language_ids = json_data.get("language", [])

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

        if (
            email
            and User.objects.filter(email=email, deleted=False)
            .exclude(id=getattr(self.instance, "id", None))
            .exists()
        ):
            errors["email"] = "An account with this email already exists"

        if (
            phone
            and User.objects.filter(phone=phone, deleted=False)
            .exclude(id=getattr(self.instance, "id", None))
            .exists()
        ):
            errors["phone"] = "An Account with this phone number already exists"

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

        education_level = None
        if education_level_id:
            education_level = EducationLevel.objects.filter(
                id=education_level_id
            ).first()
            if not education_level:
                errors["education_level"] = "Invalid education level"

        stream = None
        if stream_id:
            stream = Stream.objects.filter(id=stream_id).first()
            if not stream:
                errors["stream"] = "Invalid stream"

        languages = []
        if language_sent:
            if not isinstance(language_ids, list):
                errors["languages"] = "Language must be a list of ids"
            else:
                languages = Language.objects.filter(id__in=language_ids, deleted=False)
                if len(language_ids) != languages.count():
                    errors["language"] = "Invalid language ids"

        if medium is not None:
            valid_mediums = [
                choice[0] for choice in StudentProfile._meta.get_field("medium").choices
            ]
            if medium not in valid_mediums:
                errors["medium"] = "Invalid medium"

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
        if "education_level" in json_data:
            validated["education_level"] = education_level
        if "stream" in json_data:
            validated["stream"] = stream
        if "medium" in json_data:
            validated["medium"] = medium
        if language_sent:
            validated["language"] = list(languages)
        if "referral_code" in json_data:
            validated["referred_by"] = referred_by
        if "address" in json_data:
            address_value = (address or "").strip()
            if address_value and len(address_value) > 500:
                errors["address"] = "Address must be 500 characters or less."
            else:
                validated["address"] = address_value or None

        data["validated_data"] = validated
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        validated_data_inner = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")
        languages = validated_data_inner.pop("language", [])
        education_level = validated_data_inner.pop("education_level", None)
        stream = validated_data_inner.pop("stream", None)
        medium = validated_data_inner.pop("medium", None)
        referred_by = validated_data_inner.pop("referred_by", None)

        user = User.objects.create(
            **validated_data_inner,
            user_type=User.Role.STUDENT,
            created_by=request.user,
            terms_accepted=True,
        )
        setup_web_user_password(user)

        if profile_image_file:
            user.upload_profile_image(profile_image_file)
        profile, created = StudentProfile.objects.get_or_create(user=user)
        profile.education_level = education_level
        profile.stream = stream
        profile.medium = medium
        profile.referred_by = referred_by
        profile.save()
        if languages:
            profile.language.set(languages)
        return user

    @transaction.atomic()
    def update(self, instance, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        old_email = instance.email

        languages = data.pop("language", None)
        edu_sent = "education_level" in data
        education_level = data.pop("education_level", None)
        stream_sent = "stream" in data
        stream = data.pop("stream", None)
        medium_sent = "medium" in data
        medium = data.pop("medium", None)
        referral_sent = "referred_by" in data
        referred_by = data.pop("referred_by", None)

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save(user=request.user)

        if profile_image_file:
            instance.upload_profile_image(profile_image_file)

        try:
            profile = instance.student_profile
        except StudentProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"student_profile": "Student Profile Not found"}
            )
        if edu_sent:
            profile.education_level = education_level

        if stream_sent:
            profile.stream = stream

        if medium_sent:
            profile.medium = medium

        if referral_sent:
            profile.referred_by = referred_by

        profile.updated_by = request.user
        profile.updated_at = datetime.now()
        profile.save()

        if languages is not None:
            profile.language.set(languages)

        email_changed = old_email.lower() != instance.email.lower()
        if email_changed:
            send_email_change_notification(
                old_email=old_email,
                new_email=instance.email,
                user=instance,
            )
            setup_web_user_password(instance)

        return instance


class AdminStudentSortSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    country = serializers.IntegerField(source="user.country.id", default=None, read_only=True)
    country_name = serializers.CharField(source="user.country.name", default=None, read_only=True)
    state = serializers.IntegerField(source="user.states.id", default=None, read_only=True)
    state_name = serializers.CharField(source="user.states.name", default=None, read_only=True)
    city = serializers.IntegerField(source="user.city.id", default=None, read_only=True)
    city_name = serializers.CharField(source="user.city.name", default=None, read_only=True)
    referral_code = serializers.CharField(source="referred_by.referral_code", default=None, allow_null=True, read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            "id",
            "user",
            "language",
            "medium",
            "education_level",
            "stream",
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
            "referral_code",
        ]

class BulkUserUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    user_type = serializers.ChoiceField(choices=User.Role.choices)

    def validate_file(self, value):
        allowed_extensions = [".csv", ".xlsx", ".xls"]

        filename = value.name.lower()

        if not any(filename.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                "Only CSV, XLS and XLSX files are allowed."
            )

        return value
