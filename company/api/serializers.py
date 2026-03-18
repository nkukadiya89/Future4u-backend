from rest_framework import serializers

from company.models import Company


class CompanyCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Company
        fields = [
            "name",
            "website",
            "no_of_employees",
            "company_type",
            "company_pan",
            "gst_no",
            "about_company",
            "email",
            "phone",
            "first_name",
            "designation",
            "cin_no",
            "registered_business_address_building",
            "registered_business_address_area",
            "registered_business_address_landmark",
            "registered_business_address_state",
            "registered_business_address_city",
            "registered_business_address_pincode",
            "trading_address_building",
            "trading_address_area",
            "trading_address_landmark",
            "trading_address_state",
            "trading_address_city",
            "trading_address_pincode",
            "password",
        ]

    def validate_email(self, value):
        if self.instance and self.instance.email == value:
            return value
        if Company.objects.filter(email=value, deleted=0).exists():
            raise serializers.ValidationError("Company with this email already exists.")
        return value

    def validate_phone(self, value):
        if self.instance and self.instance.phone == value:
            return value
        if Company.objects.filter(phone=value, deleted=0).exists():
            raise serializers.ValidationError("Company with this phone already exists.")
        return value


class CompanyReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "first_name",
            "designation",
            "website",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
