from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

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
