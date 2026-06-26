from rest_framework.permissions import BasePermission

from user.models import User


class IsAdminUser(BasePermission):
    message = "Admin access required"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (
            user.is_superuser
            or user.is_staff
            or user.user_type == User.Role.SUPER_ADMIN
        )
