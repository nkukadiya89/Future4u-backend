from rest_framework import serializers

from currency.models import Currency


class CurrencySerializer(serializers.ModelSerializer):
    country_name = serializers.CharField(source="country.name", required=False)

    class Meta:
        model = Currency
        fields = [
            "id",
            "country",
            "country_name",
            "currency_name",
            "currency_code",
            "currency_symbol",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }

    def validate_currency_name(self, value):
        if Currency.objects.filter(currency_name=value).exists():
            raise serializers.ValidationError("Currency name already exists")
        return value
