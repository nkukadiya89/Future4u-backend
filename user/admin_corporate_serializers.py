import json
from django.db import transaction
from rest_framework import serializers
from city.models import City
from country.models import Country
from state.models import State
from user.models import User
from user.services.registration_service import setup_web_user_password
from email_utils.send_email import send_email_change_notification
from user_profile.models import CorporateProfile


class AdminCorporateSerializer(serializers.ModelSerializer):
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

        company_name = json_data.get("company_name")
        open_job = json_data.get("open_job")
        employees = json_data.get("employees")
        years_in_business = json_data.get("years_in_business")
        about_us = json_data.get("about_us")
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

        if open_job is not None and open_job != "" and (not isinstance(open_job, int) or open_job < 0):
            errors["open_job"] = "Open job must be a positive integer"

        if employees is not None and employees != "" and (not isinstance(employees, int) or employees < 0):
            errors["employees"] = "Employees must be a positive integer"

        if years_in_business is not None and years_in_business != "" and (
            not isinstance(years_in_business, int) or years_in_business < 0
        ):
            errors["years_in_business"] = "Years in business must be a positive integer"

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

        if "company_name" in json_data:
            validated["company_name"] = company_name
        if "open_job" in json_data:
            val = open_job
            if isinstance(val, str) and val.strip() == "":
                val = None
            validated["open_job"] = val
        if "employees" in json_data:
            val = employees
            if isinstance(val, str) and val.strip() == "":
                val = None
            validated["employees"] = val
        if "years_in_business" in json_data:
            val = years_in_business
            if isinstance(val, str) and val.strip() == "":
                val = None
            validated["years_in_business"] = val
        if "about_us" in json_data:
            validated["about_us"] = about_us
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

        company_name = data.pop("company_name", None)
        open_job = data.pop("open_job", None)
        employees = data.pop("employees", None)
        years_in_business = data.pop("years_in_business", None)
        about_us = data.pop("about_us", None)
        website = data.pop("website", None)

        user = User.objects.create(
            **data,
            user_type=User.Role.CORPORATE,
            created_by=request.user,
            terms_accepted=True,
        )

        setup_web_user_password(user)

        if profile_image_file:
            user.upload_profile_image(profile_image_file)

        CorporateProfile.objects.create(
            user=user,
            company_name=company_name,
            open_job=open_job,
            employees=employees,
            years_in_business=years_in_business,
            about_us=about_us,
            website=website,
        )

        return user

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        data = validated_data.get("validated_data", {})
        profile_image_file = validated_data.get("profile_image_file")

        old_email = instance.email

        company_name_sent = "company_name" in data
        company_name = data.pop("company_name", None)
        open_job_sent = "open_job" in data
        open_job = data.pop("open_job", None)
        employees_sent = "employees" in data
        employees = data.pop("employees", None)
        years_in_business_sent = "years_in_business" in data
        years_in_business = data.pop("years_in_business", None)
        about_us_sent = "about_us" in data
        about_us = data.pop("about_us", None)
        website_sent = "website" in data
        website = data.pop("website", None)

        for attr, value in data.items():
            setattr(instance, attr, value)

        instance.save(user=request.user)

        if profile_image_file:
            instance.upload_profile_image(profile_image_file)

        try:
            profile = instance.corporate_profile
        except CorporateProfile.DoesNotExist:
            raise serializers.ValidationError(
                {"corporate_profile": "Corporate Profile not found"}
            )

        if company_name_sent:
            profile.company_name = company_name
        if open_job_sent:
            profile.open_job = open_job
        if employees_sent:
            profile.employees = employees
        if years_in_business_sent:
            profile.years_in_business = years_in_business
        if about_us_sent:
            profile.about_us = about_us
        if website_sent:
            profile.website = website

        profile.save()

        if old_email.lower() != instance.email.lower():
            send_email_change_notification(
                old_email=old_email,
                new_email=instance.email,
                user=instance,
            )
            setup_web_user_password(instance)

        return instance
    
class AdminCorporateSortSerializer(serializers.ModelSerializer):
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
        model = CorporateProfile
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
            "company_name",
            "open_job",
            "employees",
            "years_in_business",
            "about_us",
            "website",
        ]