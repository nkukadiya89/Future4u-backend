from rest_framework.permissions import IsAuthenticated


class StreamMasterPermission(IsAuthenticated):
    message = "Authentication required."
