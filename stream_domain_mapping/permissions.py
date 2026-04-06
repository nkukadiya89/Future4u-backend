from rest_framework.permissions import IsAuthenticated


class StreamDomainMappingPermission(IsAuthenticated):
    message = "Authentication required."
