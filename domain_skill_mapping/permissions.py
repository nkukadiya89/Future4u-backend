from rest_framework.permissions import IsAuthenticated


class DomainSkillMappingPermission(IsAuthenticated):
    message = "Authentication required."
