from __future__ import annotations

from typing import Any

from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin/staff users."""

    def has_permission(self, request: Any, view: Any) -> bool:  # pragma: no cover - trivial
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsAuthorOrAdmin(permissions.BasePermission):
    """Allow access if the user is the author of the object or an admin."""

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        # For list/detail that don't use object-level checks, default to allow
        if not hasattr(obj, "created_by"):
            return False
        return bool(request.user and request.user.is_authenticated and (obj.created_by_id == request.user.id or request.user.is_staff))
