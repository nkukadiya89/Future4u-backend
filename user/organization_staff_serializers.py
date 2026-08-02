import json

from django.db import transaction
from rest_framework import serializers

from city.models import City
from common.serializers import BaseModelSerializer
from country.models import Country
from email_utils.send_email import send_email_change_notification
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password


class OrganizationStaffSerializer(BaseModelSerializer):
    """Create/update staff users owned by an organization admin.

    Identity only — user_type is inherited from the creator, is_org_staff=True.
    No role assignment and no token logic here (roles go through the existing
    assign-user-group endpoint; the staff token rule lives in the profile signal
    and utils/token_check.py).
    """

    data = serializers.CharField(write_only=True, required=False)
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

        errors = {}
        is_update = self.instance is not None

        email = (json_data.get("email") or "").strip().lower()
        first_name = (json_data.get("first_name") or "").strip()
        last_name = (json_data.get("last_name") or "").strip()
        phone = (json_data.get("phone") or "").strip()
        address = (json_data.get("address") or "").strip()

        country_id = json_data.get("country")
        state_id = json_data.get("state")
        city_id = json_data.get("city")

        if not is_update:
            if not email:
                errors["email"] = "This field is required."
            if not first_name:
                errors["first_name"] = "This field is required."

        if (
            email
            and User.objects.filter(email__iexact=email, deleted=False)
            .exclude(id=getattr(self.instance, "id", None))
            .exists()
        ):
            errors["email"] = "An account with this email already exists."

        if (
            phone
            and User.objects.filter(phone=phone, deleted=False)
            .exclude(id=getattr(self.instance, "id", None))
            .exists()
        ):
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

        validated = {}

        if not is_update or email:
            validated["email"] = email
        if not is_update or first_name:
            validated["first_name"] = first_name
        if "last_name" in json_data:
            validated["last_name"] = last_name or ""
        if "phone" in json_data:
            validated["phone"] = phone or None
        if "address" in json_data:
            validated["address"] = address or None
        if "country" in json_data:
            validated["country"] = country
        if "state" in json_data:
            validated["states"] = state
        if "city" in json_data:
            validated["city"] = city

        data["validated_data"] = validated
        data["profile_image_file"] = self.context["request"].FILES.get("profile_image")
        return data

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        creator = request.user

        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        staff = User(
            **data,
            user_type=creator.user_type,
            created_by=creator,
            is_org_staff=True,
            terms_accepted=True,
            status="pending",
            is_active=False,
            email_verified=False,
            must_change_password=True,
        )
        # Explicit intent: staff are created with zero groups (roles are
        # assigned later via assign-user-group). The durable enforcement lives
        # in User.save() via the is_org_staff guard; this flag documents the
        # intent at the call site.
        staff.save(skip_group_assignment=True)

        setup_web_user_password(staff)

        if profile_image_file:
            staff.upload_profile_image(profile_image_file)

        return staff

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        old_email = instance.email

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save(user=request.user)

        if profile_image_file:
            instance.upload_profile_image(profile_image_file)

        email_changed = old_email.lower() != instance.email.lower()
        if email_changed:
            send_email_change_notification(
                old_email=old_email,
                new_email=instance.email,
                user=instance,
            )
            setup_web_user_password(instance)

        return instance


class OrganizationStaffListSerializer(BaseModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    states_name = serializers.CharField(source="states.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = BaseModelSerializer.Meta.fields + [
            "id",
            "first_name",
            "last_name",
            "user_type",
            "is_org_staff",
            "groups",
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

    def get_groups(self, obj):
        return list(obj.groups.values_list("name", flat=True))
