from django.utils.timezone import now
from rest_framework import serializers
from city_areas.models import CityArea
from utils.datetime_formatter import format_datetime


class CityAreaSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CityArea
        fields = [
            "id",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "city_area_name",
            "zipcode",
            "created_by",
            "updated_by",
            "created_by_name",
            "updated_by_name",
            "created_at",
            "updated_at",
            "deleted",
        ]

        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def get_created_at(self, obj):
        return format_datetime(getattr(obj, "created_at", None))

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else None

    def get_updated_at(self, obj):
        return format_datetime(getattr(obj, "updated_at", None))

    def get_updated_by_name(self, obj):
        return f"{obj.updated_by.first_name} {obj.updated_by.last_name}" if obj.updated_by else None

    def validate(self, data):
        city_area_name = data.get("city_area_name")
        city = data.get("city")
        instance = getattr(self, "instance", None)

        # Check for duplicate city area name in the same city
        if city_area_name and city:
            name_queryset = CityArea.objects.filter(city_area_name=city_area_name, city=city, deleted=False)
            if instance:
                name_queryset = name_queryset.exclude(pk=instance.pk)
            if name_queryset.exists():
                raise serializers.ValidationError("City Area with this name already exists in this City")

        return data

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = CityArea(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for field in ["country", "state", "city", "city_area_name", "zipcode", "deleted"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance


class CityAreaArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CityArea
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for deleted_id in deleted_ids:
            try:
                city_area = CityArea.objects.get(id=deleted_id)
                city_area.deleted = True
                if hasattr(city_area, "deleted_by"):
                    city_area.deleted_by = user
                if hasattr(city_area, "deleted_at"):
                    city_area.deleted_at = now()
                city_area.save()
            except CityArea.DoesNotExist:
                raise serializers.ValidationError("City Area does not exist")

        return city_area


class CityAreaRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = CityArea
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                city_area = CityArea.objects.get(id=deleted_id)
                city_area.deleted = False
                city_area.deleted_at = None
                city_area.deleted_by = None
                city_area.updated_at = now()
                city_area.save()
            except CityArea.DoesNotExist:
                raise serializers.ValidationError("City Area does not exist")

        return city_area


class CityAreaArchiveListSerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    state_name = serializers.CharField(source="state.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    deleted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CityArea
        fields = [
            "id",
            "country",
            "country_name",
            "state",
            "state_name",
            "city",
            "city_name",
            "city_area_name",
            "zipcode",
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
