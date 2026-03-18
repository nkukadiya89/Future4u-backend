from rest_framework import serializers

from newsletter.models import NewsLetter


class NewsLetterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsLetter
        fields = [
            "id",
            "email",
            "subscribe",
            "unsubscribe_reason",
            "created_by",
            "updated_by",
        ]

        extrs_kwargs = {
            "created_by": {"write_only": True},
            "updated_by": {"write_only": True},
        }
