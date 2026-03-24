from rest_framework.permissions import IsAuthenticated


class EducationLevelMasterPermission(IsAuthenticated):
    message = "Authentication required."
