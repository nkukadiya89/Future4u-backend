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

class IsSchoolCollegeOrInstittute(BasePermission):
    message = ("Only School/college or Institute users can manage students")

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        return (
            user.user_type 
            in[
                User.Role.SCHOOL_COLLEGE,
                User.Role.INSTITUTE,
            ]
            and user.is_active
            and user.status == "active"
            and not user.deleted
        )
     