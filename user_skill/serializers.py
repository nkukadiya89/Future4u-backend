from rest_framework import serializers

from user_skill.models import UserSkill


class UserSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSkill
        fields = [
            "id",
            "user",
            "skill",
            "proficiency_score",
            "is_active",
            "deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request") if hasattr(self, "context") else None
        req_user = getattr(request, "user", None) if request else None
        skill = attrs.get("skill", getattr(self.instance, "skill", None))

        if req_user and skill:
            exists = UserSkill.objects.filter(user=req_user, skill=skill)
            if self.instance:
                exists = exists.exclude(pk=self.instance.pk)
            if exists.exists():
                raise serializers.ValidationError(
                    {
                        "skill": "This user already has a proficiency entry for this skill."
                    }
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None) if request else None
        return UserSkill.objects.create(user=user, **validated_data)
