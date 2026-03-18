from rest_framework import serializers

from activity_log.models import ActivityLog, WhatsAppMessageLog


class WhatsAppMessageLogSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%d-%m-%y %H:%M:%S")
    company_name = serializers.CharField(source="company.name", default=None)
    vendor_name = serializers.CharField(source="vendor.name", default=None)

    class Meta:
        model = WhatsAppMessageLog
        fields = [
            "id",
            "company",
            "company_name",
            "vendor",
            "vendor_name",
            "phone_number",
            "request_user",
            "template_name",
            "response_code",
            "response_content",
            "created_at",
            "activity",
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    changed_at = serializers.DateTimeField(format="%d-%m-%y %H:%M:%S")
    company_name = serializers.CharField(source="company.name", default=None)
    vendor_name = serializers.CharField(source="vendor.name", default=None)
    employee_name = serializers.CharField(source="employee.first_name", default=None)
    email = serializers.CharField(source="user.email")
    phone = serializers.CharField(source="user.phone")
    person_name = serializers.CharField(source="user.first_name")

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "details",
            "company_name",
            "vendor_name",
            "employee_name",
            "event_type",
            "email",
            "phone",
            "person_name",
            "changed_at",
            "ip_address",
        ]
