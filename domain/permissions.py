from rest_framework.permissions import IsAuthenticated


class DomainMasterPermission(IsAuthenticated):
    message = "Authentication required."
