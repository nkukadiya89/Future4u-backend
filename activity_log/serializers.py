from rest_framework import serializers

from activity_log.models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    changed_at = serializers.DateTimeField(format="%d-%m-%y %H:%M")
    company_name = serializers.CharField(source="company.name", default=None)
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
            "employee_name",
            "event_type",
            "email",
            "phone",
            "person_name",
            "changed_at",
            "ip_address",
        ]
