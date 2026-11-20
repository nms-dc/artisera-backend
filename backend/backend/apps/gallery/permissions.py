from rest_framework.exceptions import PermissionDenied

from accounts.models import RM_ROLE_ID


def require_permission(user, resource, action):
    if not user.can(resource, action):
        raise PermissionDenied("You do not have permission to do this.")


def _is_rm(user):
    return user.role_id == RM_ROLE_ID


def scope_sales(queryset, user):
    """RMs only see sales of their own inquiries."""
    return queryset.filter(inquiry__rm=user) if _is_rm(user) else queryset


def scope_orders(queryset, user):
    """RMs only see orders of their own sales."""
    return queryset.filter(sale__inquiry__rm=user) if _is_rm(user) else queryset


def scope_customers(queryset, user):
    """Customers who have sales; an RM sees only customers of their own sales."""
    filters = {"inquiries__sale__isnull": False}
    if _is_rm(user):
        filters["inquiries__rm"] = user
    # Both conditions go in one filter() call so they apply to the same inquiry.
    return queryset.filter(**filters).distinct()
