from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from pincode.models import PinCode


class PinCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PinCode
        fields = [
            "id",
            "pincode_number",
            "city_name",
            "state_name",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate(self, data):
        pincode_number = data.get("pincode_number")
        if self.instance and self.instance.pincode_number == pincode_number:
            return data

        if PinCode.objects.filter(pincode_number=pincode_number).exists():
            raise ValidationError(f"This Pincode {pincode_number} is already exist")

        return data


# Pincode Multiple Deleted
class PinCodeDeleteSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PinCode
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                pincode = PinCode.objects.get(id=deleted_id)
                pincode.deleted = 1
                pincode.save()
            except PinCode.DoesNotExist:
                raise serializers.ValidationError("Pincode does not exist")

        return pincode


# Pincode Multiple Archive
class PinCodeArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = PinCode
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                pincode = PinCode.objects.get(id=deleted_id)
                pincode.deleted = 0
                pincode.save()
            except PinCode.DoesNotExist:
                raise serializers.ValidationError("Pincode does not exist")

        return pincode
