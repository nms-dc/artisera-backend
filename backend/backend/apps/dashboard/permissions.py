from rest_framework.permissions import BasePermission
from accounts.models import RM_ROLE_ID


class IsAdminUser(BasePermission):
    message = "Admin only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_admin
        )


class IsAdminOrRM(BasePermission):
    message = "Admin or RM only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_admin
                or request.user.role_id == "RM"
            )
        )