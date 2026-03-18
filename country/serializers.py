from django.utils.timezone import now
from rest_framework import serializers

from country.models import Country
from utils.datetime_formatter import format_datetime


class CountrySerializers(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
            "unicode",
            "country_flag",
            "phone_code",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
            "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
            "unicode": {"required": False, "allow_null": True, "allow_blank": True},
            "country_flag": {"required": False, "allow_null": True, "allow_blank": True},
        }

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = Country(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field in [
            "name",
            "code",
            "unicode",
            "country_flag",
            "phone_code",
            "deleted",
        ]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance


class CountryArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Country
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for deleted_id in deleted_ids:
            try:
                country = Country.objects.get(id=deleted_id)
                country.deleted = True
                if hasattr(country, "deleted_by"):
                    country.deleted_by = user
                if hasattr(country, "deleted_at"):
                    country.deleted_at = now()
                country.save()
            except Country.DoesNotExist:
                raise serializers.ValidationError("Country does not exist")

        return country


# Country Archive Serializer
class CountryRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = Country
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                country = Country.objects.get(id=deleted_id)
                country.updated_at = now()
                country.deleted = False
                country.deleted_at = None
                country.deleted_by = None
                country.save()
            except Country.DoesNotExist:
                raise serializers.ValidationError("Country does not exist")

        return country


class CountryArchiveListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
            "unicode",
            "country_flag",
            "phone_code",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
            "deleted",
        ]

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def get_deleted_at(self, obj):
        return format_datetime(getattr(obj, "deleted_at", None))

    def get_deleted_by_name(self, obj):
        return f"{obj.deleted_by.first_name} {obj.deleted_by.last_name}" if obj.deleted_by else None
