from rest_framework.permissions import IsAuthenticated


class DomainCareerMappingPermission(IsAuthenticated):
    message = "Authentication required."

