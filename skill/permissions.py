from rest_framework.permissions import IsAuthenticated


class SkillMasterPermission(IsAuthenticated):
    message = "Authentication required."

