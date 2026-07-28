import json

from django.db import transaction
from rest_framework import serializers

from city.models import City
from common.serializers import BaseModelSerializer
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password
from user_profile.models import StudentProfile


class OrganizationStudentCreateSerializer(BaseModelSerializer):
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

        student = User.objects.create(
            **validated_data_inner,
            user_type=User.Role.STUDENT,
            created_by=creator,
            terms_accepted=True,
            status="pending",
            is_active=False,
            email_verified=False,
            must_change_password=True,
        )
        setup_web_user_password(student)

        student.created_by = creator
        student.save(update_fields=["created_by"])

        StudentProfile.objects.get_or_create(user=student)
        if profile_image_file:
            student.upload_profile_image(profile_image_file)

        return student


class OrganizationStudentListSerializer(BaseModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    states_name = serializers.CharField(source="states.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    education_level = serializers.CharField(
        source="student_profile.education_level.display_name",
        read_only=True,
        default=None,
    )
    assessment_status = serializers.SerializerMethodField()
    recommendation_score = serializers.SerializerMethodField()
    last_active = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "first_name",
            "last_name",
            "user_type",
            "education_level",
            "assessment_status",
            "recommendation_score",
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

    def get_assessment_status(self, obj):
        assessment = (
            obj.student_assessments.filter(deleted=False)
            .order_by("-created_at")
            .first()
        )
        if not assessment:
            return "Pending"
        return "Completed" if assessment.is_completed else "In-Progress"

    def get_recommendation_score(self, obj):
        assessment = (
            obj.student_assessments.filter(deleted=False)
            .order_by("-created_at")
            .first()
        )
        if not assessment:
            return None
        if not assessment.is_completed:
            return None
        recommendation = (
            obj.career_recommendations.filter(
                deleted=False,
                profile_type="student",
                student_assessment_id=assessment.id,
            )
            .order_by("-created_at")
            .first()
        )

        if not recommendation:
            return None

        if recommendation:
            top = recommendation.suggestions.order_by("-match_percentage").first()
            return f"{top.match_percentage}%" if top else None
        return None

    def get_last_active(self, obj):
        return obj.last_login.date().isoformat() if obj.last_login else None
