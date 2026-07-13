from django.utils.timezone import now
from rest_framework import serializers

from common.mixins.serializer_mixins import (
    DateFieldsMixin,
    DeletedFieldsMixin,
    UserNameMixin,
)
from state.models import State


class StateSerializer(DateFieldsMixin, UserNameMixin, serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", read_only=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = State
        fields = [
            "id",
            "name",
            "country",
            "country_name",
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

    def validate(self, attrs):
        name = attrs.get("name")
        country = attrs.get("country")
        instance = getattr(self, "instance", None)
        existing_query = State.objects.filter(name=name, country=country, deleted=False)
        if instance:
            existing_query = existing_query.exclude(pk=instance.pk)
        if existing_query.exists():
            raise serializers.ValidationError(
                f"{name} already exists in {country.name}"
            )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance = State(**validated_data)
        instance.created_by = user
        instance.created_at = now()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for field in ["name", "country", "deleted"]:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        instance.updated_by = user
        instance.updated_at = now()
        instance.save()
        return instance


class StateArchiveSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = State
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        for deleted_id in deleted_ids:
            try:
                state = State.objects.get(id=deleted_id)
                state.deleted = True
                if hasattr(state, "deleted_by"):
                    state.deleted_by = user
                if hasattr(state, "deleted_at"):
                    state.deleted_at = now()
                state.save()
            except State.DoesNotExist:
                raise serializers.ValidationError("State does not exist")

        return state


class StateRestoreSerializer(serializers.ModelSerializer):
    deleted = serializers.ListField(write_only=True)

    class Meta:
        model = State
        fields = ["deleted"]

    def create(self, validated_data):
        deleted_ids = validated_data.pop("deleted", [])
        for deleted_id in deleted_ids:
            try:
                state = State.objects.get(id=deleted_id)
                state.deleted = False
                state.deleted_at = None
                state.deleted_by = None
                state.updated_at = now()
                state.save()
            except State.DoesNotExist:
                raise serializers.ValidationError("State does not exist")

        return state


class StateArchiveListSerializer(
    DateFieldsMixin,
    UserNameMixin,
    DeletedFieldsMixin,
    serializers.ModelSerializer,
):
    country_name = serializers.CharField(source="country.name", read_only=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_by_name = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)
    deleted_by_name = serializers.SerializerMethodField(read_only=True)
    deleted_at = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = State
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "deleted_by_name",
            "deleted_at",
            "deleted",
        ]
