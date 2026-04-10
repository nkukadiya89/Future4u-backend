from rest_framework.permissions import IsAuthenticated


class LanguageMasterPermission(IsAuthenticated):
    message = "Authentication required."
