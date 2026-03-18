from rest_framework import serializers

from user_profile.models import BusinessSetting


class BusinessSettingSerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessSetting
        fields = [
            "id",
            "company",
            "partner_company",
            "end_client",
            "user_id",
            "notifications",
            "sgst",
            "cgst",
            "igst",
            "country",
            "state",
            "city",
            "currency",
            "created_by",
            "updated_by",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def to_representation(self, instance):
        response_data = super().to_representation(instance)
        return response_data

    # Helper Function to reduce fetching instances
    def get_instance(self, model, id, error_message):
        try:
            return model.objects.get(id=id)
        except model.DoesNotExist:
            raise serializers.ValidationError({"success": False, "message": error_message})

    def update(self, instance, validated_data):
        # Update instance attributes with validated data
        instance.company = validated_data.get("company", instance.company)
        instance.partner_company = validated_data.get("partner_company", instance.partner_company)
        instance.end_client = validated_data.get("end_client", instance.end_client)
        instance.notifications = validated_data.get("notifications", instance.notifications)
        instance.sgst = validated_data.get("sgst", instance.sgst)
        instance.cgst = validated_data.get("cgst", instance.cgst)
        instance.igst = validated_data.get("igst", instance.igst)
        instance.country = validated_data.get("country", instance.country)
        instance.state = validated_data.get("state", instance.state)
        instance.city = validated_data.get("city", instance.city)
        instance.currency = validated_data.get("currency", instance.currency)

        # Save instance
        instance.save()
        return instance


class BusinessSettingInfoSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", required=False)
    partner_company_name = serializers.CharField(source="partner_company.company_name", required=False)
    end_client_name = serializers.CharField(source="end_client.name", required=False, allow_null=True)
    country_name = serializers.CharField(source="country.name", required=False, allow_null=True)
    state_name = serializers.CharField(source="state.name", required=False, allow_null=True)
    city_name = serializers.CharField(source="city.name", required=False, allow_null=True)

    class Meta:
        model = BusinessSetting
        fields = [
            "id",
            "company",
            "company_name",
            "partner_company",
            "partner_company_name",
            "end_client",
            "end_client_name",
            "notifications",
            "sgst",
            "cgst",
            "igst",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "currency",
        ]
