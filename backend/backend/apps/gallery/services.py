from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
import logging

from accounts.models import User

logger = logging.getLogger(__name__)

GALLERY_MANAGER_ROLE_NAME = "Gallery Manager"

SEPARATE_CERTIFICATE_PLAN = "Send Separately"

# Derived order statuses
PREPARATION = "Preparation"
PACKING_DISPATCH = "Packing & Dispatch"
SHIPPED = "Shipped"
DELIVERED = "Delivered"

DELIVERED_Q = Q(received_at__isnull=False) | Q(shipment_status=DELIVERED)
SHIPPED_Q = ~DELIVERED_Q & Q(actual_dispatch_date__isnull=False)
PACKING_Q = ~DELIVERED_Q & Q(actual_dispatch_date__isnull=True, ready_for_packing=True)
PREPARATION_Q = ~DELIVERED_Q & Q(
    actual_dispatch_date__isnull=True, ready_for_packing=False
)

CERTIFICATE_PENDING_Q = Q(
    sale__certificate_plan=SEPARATE_CERTIFICATE_PLAN,
    certificate_sent_at__isnull=True,
)

IN_STOCK_STATUS = "In Stock"


def derive_status(order):
    """Python twin of the Q objects above; keep the two in sync."""
    if order.received_at or order.shipment_status == DELIVERED:
        return DELIVERED
    if order.actual_dispatch_date:
        return SHIPPED
    if order.ready_for_packing:
        return PACKING_DISPATCH
    return PREPARATION


# --- Sale "pending with" -------------------------------------------------
PENDING_RM_EMAIL = "RM email not received"

# Sales that have a pendingWith reason (Q twin of sale_pending_with below).
SALE_PENDING_Q = Q(email_status__received_at__isnull=True)


def sale_email_confirmed(sale):
    try:
        return sale.email_status.received_at is not None
    except ObjectDoesNotExist:
        return False


def sale_pending_with(sale):
    if not sale_email_confirmed(sale):
        return PENDING_RM_EMAIL
    return None


def gallery_manager_users():
    return User.objects.filter(
        is_active=True, role__name__iexact=GALLERY_MANAGER_ROLE_NAME
    )


def notify_gallery_managers(event, *, title, text, sale=None, order=None, actor=None):
    """
    Single place that notifies Gallery Managers (SALE_EMAIL_SENT, ORDER_CREATED, ...).

    PLACEHOLDER: this finds the recipients but only logs, because the project's
    notifications app has not been shared yet. Replace the loop body with the
    real notification-creation call.
    """
    for recipient in gallery_manager_users():
        logger.info("Notify %s [%s]: %s - %s", recipient.email, event, title, text)


# orderStatus query values -> order filters (used by the sales list)
ORDER_STATUS_FILTERS = {
    "Preparation": PREPARATION_Q,
    "Packing": PACKING_Q,
    "Dispatched": SHIPPED_Q,
    "Delivered": DELIVERED_Q,
    "Certificates Pending": CERTIFICATE_PENDING_Q,
}
ORDER_STATUS_NONE = "none"  # sales that have no orders yet

CERTIFICATE_STATUSES = ("pending", "sent", "with-shipment")
COMMISSION_STATUS = "Commission"


def order_suffix(index):
    """0 -> A, 1 -> B, ... 25 -> Z, 26 -> AA"""
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


# `status` query values for the orders list -> order filters
ORDER_LIST_STATUS_FILTERS = {
    "Preparation": PREPARATION_Q,
    "Packing & Dispatch": PACKING_Q,
    "Packing": PACKING_Q,
    "Shipped": SHIPPED_Q,
    "Dispatched": SHIPPED_Q,
    "Delivered": DELIVERED_Q,
}


def can_access_order(user, order):
    """Admins and non-RM roles see every order; an RM only their own sales' orders."""
    if not _is_rm(user):
        return True
    return order.sale.inquiry.rm_id == user.id


# Starting lists; the spec only shows "Tube" and "DHL". Edit here to change them.
PACKAGING_TYPES = ["Tube", "Box", "Crate", "Envelope", "Pallet", "Other"]
COURIERS = ["DHL", "FedEx", "UPS", "Blue Dart", "DTDC", "India Post", "Other"]
SHIPMENT_STATUSES = ("In Transit", "Delivered")
