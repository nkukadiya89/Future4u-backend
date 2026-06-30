from __future__ import annotations

from typing import Any

from rest_framework import permissions


class IsNotificationOwner(permissions.BasePermission):
    """Allow access only to the owner of the notification."""

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
