from rest_framework.permissions import IsAuthenticated


class CareerMasterPermission(IsAuthenticated):
    message = "Authentication required."

