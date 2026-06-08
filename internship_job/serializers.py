from .models import Internship
from rest_framework import serializers
from common.serializers import BaseModelSerializer

class InternshipSerializer(BaseModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    provider_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Internship
        fields= BaseModelSerializer.Meta.fields+[
            "id",
            "name",
            "city",
            "city_name",
            "organization_name",
            "description",
            "responsibilities",
            "skills",
            "education_tags",
            "why_this_match",
            "internship_type",
            "mode",
            "duration",
            "fees_amount",
            "stipend_amount",
            "certificate_provided",
            "provider",
            "provider_name",
        ]
    def get_provider_name(self, obj):
        if obj.provider:
            return obj.provider.full_name
        return None