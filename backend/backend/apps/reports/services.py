from datetime import datetime, time

from django.db.models import Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from inquiries.models import Inquiry


def get_inquiry_summary(
    from_date=None,
    to_date=None,
    rm_id=None,
    category_id=None,
    inquiry_status=None,
):
    inquiries = Inquiry.objects.all()

    # Date filters
    if from_date:
        from_datetime = timezone.make_aware(
            datetime.combine(from_date, time.min)
        )
        inquiries = inquiries.filter(created_at__gte=from_datetime)

    if to_date:
        to_datetime = timezone.make_aware(
            datetime.combine(to_date, time.max)
        )
        inquiries = inquiries.filter(created_at__lte=to_datetime)

    # RM filter
    if rm_id:
        inquiries = inquiries.filter(rm_id=rm_id)

    # Category filter
    if category_id:
        inquiries = inquiries.filter(category_id=category_id)

    # Status filter
    if inquiry_status:
        inquiries = inquiries.filter(status=inquiry_status)

    # -----------------------------------------------
    # Status counts
    # -----------------------------------------------

    status_counts = dict(
        inquiries.values("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    # -----------------------------------------------
    # KPIs
    # -----------------------------------------------

    kpis = {
        "total": inquiries.count(),
        "touchbase": status_counts.get(
            Inquiry.Status.TOUCHBASE, 0
        ),
        "followUp": status_counts.get(
            Inquiry.Status.TOUCHBASE_FOLLOWUP, 0
        ),
        "active": status_counts.get(
            Inquiry.Status.ACTIVE_CONVERSATIONS, 0
        ),
        "nurture": status_counts.get(
            Inquiry.Status.NURTURE, 0
        ),
        "won": status_counts.get(
            Inquiry.Status.WON, 0
        ),
        "lost": status_counts.get(
            Inquiry.Status.LOST, 0
        ),
    }

    # -----------------------------------------------
    # By Status — ALL 6 statuses
    # -----------------------------------------------

    by_status = [
        {
            "status": status_value,
            "count": status_counts.get(status_value, 0),
        }
        for status_value, _ in Inquiry.Status.choices
    ]

    # -----------------------------------------------
    # By Category — TOP 5
    # -----------------------------------------------

    by_category_data = (
        inquiries
        .values("category__name")
        .annotate(count=Count("id"))
        .order_by("-count", "category__name")[:5]
    )

    by_category = [
        {
            "category": item["category__name"] or "Uncategorized",
            "count": item["count"],
        }
        for item in by_category_data
    ]

    # -----------------------------------------------
    # By RM — TOP 5
    # -----------------------------------------------

    by_rm_data = (
        inquiries
        .values("rm__name")
        .annotate(count=Count("id"))
        .order_by("-count", "rm__name")[:5]
    )

    by_rm = [
        {
            "rm": item["rm__name"] or "Unassigned",
            "count": item["count"],
        }
        for item in by_rm_data
    ]

    return {
        "kpis": kpis,
        "byStatus": by_status,
        "byCategory": by_category,
        "byRm": by_rm,
    }

def get_inquiry_detail_report(
    from_date=None,
    to_date=None,
    inquiry_status=None,
    q=None,
    page=1,
    page_size=10,
):
    inquiries = (
        Inquiry.objects
        .select_related(
            "customer",
            "category",
            "subcategory",
            "artist",
            "rm",
        )
        .all()
    )

    # ==================================================
    # DATE FILTERS
    # ==================================================

    if from_date:
        from_datetime = timezone.make_aware(
            datetime.combine(from_date, time.min)
        )
        inquiries = inquiries.filter(
            created_at__gte=from_datetime
        )

    if to_date:
        to_datetime = timezone.make_aware(
            datetime.combine(to_date, time.max)
        )
        inquiries = inquiries.filter(
            created_at__lte=to_datetime
        )

    # ==================================================
    # STATUS FILTER
    # ==================================================

    if inquiry_status:
        inquiries = inquiries.filter(
            status=inquiry_status
        )

    # ==================================================
    # SEARCH
    # ==================================================

    if q:
        inquiries = inquiries.filter(
            Q(code__icontains=q)
            | Q(customer__name__icontains=q)
            | Q(customer__email__icontains=q)
            | Q(customer__phone__icontains=q)
            | Q(requirement__icontains=q)
        )

    inquiries = inquiries.order_by("-created_at")

    paginator = Paginator(inquiries, page_size)
    page_obj = paginator.get_page(page)

    results = []

    for obj in page_obj.object_list:
        results.append({
            "id": str(obj.id),
            "code": obj.code,

            "customer": {
                "id": str(obj.customer.id),
                "code": obj.customer.code,
                "name": obj.customer.name,
                "phone": obj.customer.phone,
                "email": obj.customer.email,
                "location": obj.customer.location,
                "state": obj.customer.state,
            },

            "inquiryType": obj.inquiry_type,
            "requirement": obj.requirement,
            "quantity": obj.quantity,

            "value": (
                float(obj.value)
                if obj.value is not None
                else None
            ),

            "category": (
                {
                    "id": str(obj.category.id),
                    "name": obj.category.name,
                }
                if obj.category
                else None
            ),

            "subcategory": (
                {
                    "id": str(obj.subcategory.id),
                    "name": obj.subcategory.name,
                }
                if obj.subcategory
                else None
            ),

            "artist": (
                {
                    "id": str(obj.artist.id),
                    "name": obj.artist.name,
                }
                if obj.artist
                else None
            ),

            "source": obj.source,
            "priority": obj.priority,
            "status": obj.status,

            "rm": (
                {
                    "id": str(obj.rm.id),
                    "name": obj.rm.name,
                }
                if obj.rm
                else None
            ),

            "assignedOn": obj.assigned_on,
            "nextFollowUp": obj.next_follow_up,
            "nextAction": (
                obj.next_action
                if obj.next_action
                else None
            ),
            "lastContact": obj.last_contact,
            "closedAt": obj.closed_at,
            "notes": obj.notes,

            "expectedTimeline": obj.expected_timeline,
            "budgetRange": obj.budget_range,
            "artStyle": obj.art_style,

            "createdAt": obj.created_at,
            "updatedAt": obj.updated_at,
        })

    return {
        "count": paginator.count,
        "page": page_obj.number,
        "pageSize": page_size,
        "results": results,
    }