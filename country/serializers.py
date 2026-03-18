from rest_framework import serializers

from country.models import Country


class CountrySerializers(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
            "unicode",
            "country_flag",
            "created_by",
            "updated_by",
            "deleted",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }
