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

def is_admin_user(user):
    return (
        user.is_superuser
        or user.is_staff
        or user.user_type == User.Role.SUPER_ADMIN
    )


class IsAdminOrProvider(BasePermission):
    message = "Provider or admin access required"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_admin_user(user):
            return True
        return (
            user.user_type
            in [
                User.Role.INSTITUTE,
                User.Role.SCHOOL_COLLEGE,
                User.Role.CORPORATE,
            ]
            and user.is_active
            and user.status == "active"
            and not user.deleted
        )

class IsSchoolCollegeOrInstitute(BasePermission):
    message = (
        "This feature is available for School/College or Institute users only."
    )

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


class IsIndividualUser(BasePermission):
    message = (
        "This feature is available for students, parents, and working "
        "professionals only."
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_admin_user(user):
            return True
        return (
            user.user_type
            in [
                User.Role.STUDENT,
                User.Role.PARENT,
                User.Role.PROFESSIONAL,
            ]
            and user.is_active
            and user.status == "active"
            and not user.deleted
        )
     