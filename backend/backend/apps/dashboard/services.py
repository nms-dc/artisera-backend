from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from accounts.models import User, RM_ROLE_ID
from inquiries.models import Inquiry


ACTIVE_STATUSES = [
    Inquiry.Status.TOUCHBASE,
    Inquiry.Status.TOUCHBASE_FOLLOWUP,
    Inquiry.Status.ACTIVE_CONVERSATIONS,
    Inquiry.Status.NURTURE,
]


def get_admin_dashboard(range_days=30):
    now = timezone.now()
    start_date = now - timedelta(days=range_days)

    # ==================================================
    # BASE QUERYSET
    # ==================================================
    inquiries = Inquiry.objects.filter(
        created_at__gte=start_date
    )

    # ==================================================
    # KPIs
    # ==================================================
    total = inquiries.count()

    unassigned = inquiries.filter(
        rm__isnull=True
    ).count()

    active = inquiries.filter(
        status__in=ACTIVE_STATUSES
    ).count()

    active_conversations = inquiries.filter(
        status=Inquiry.Status.ACTIVE_CONVERSATIONS
    ).count()

    won_inquiries = inquiries.filter(
        status=Inquiry.Status.WON
    )

    won_count = won_inquiries.count()

    won_revenue = (
        won_inquiries.aggregate(total=Sum("value"))["total"]
        or 0
    )

    lost_count = inquiries.filter(
        status=Inquiry.Status.LOST
    ).count()

    # ==================================================
    # BY SOURCE - ALL 8 SOURCES
    # ==================================================
    source_counts = dict(
        inquiries.values("source")
        .annotate(count=Count("id"))
        .values_list("source", "count")
    )

    by_source = [
        {
            "source": source,
            "count": source_counts.get(source, 0),
        }
        for source, _ in Inquiry.Source.choices
    ]

    # ==================================================
    # BY TYPE - ALL 4 TYPES
    # ==================================================
    type_counts = dict(
        inquiries.values("inquiry_type")
        .annotate(count=Count("id"))
        .values_list("inquiry_type", "count")
    )

    by_type = [
        {
            "type": inquiry_type,
            "count": type_counts.get(inquiry_type, 0),
        }
        for inquiry_type, _ in Inquiry.InquiryType.choices
    ]

    # ==================================================
    # TREND - EXACTLY 13 WEEKS
    # ==================================================
    trend_start = now - timedelta(weeks=12)

    trend_data = (
        Inquiry.objects
        .filter(created_at__gte=trend_start)
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(count=Count("id"))
        .order_by("week")
    )

    trend_counts = {
        item["week"].date(): item["count"]
        for item in trend_data
    }

    current_week = (
        now.date()
        - timedelta(days=now.weekday())
    )

    trend = []

    for weeks_ago in range(12, -1, -1):
        week_start = current_week - timedelta(
            weeks=weeks_ago
        )

        week_datetime = timezone.make_aware(
            timezone.datetime.combine(
                week_start,
                timezone.datetime.min.time(),
            )
        )

        trend.append({
            "weekStart": (
                week_datetime.isoformat()
                .replace("+00:00", "Z")
            ),
            "count": trend_counts.get(
                week_start,
                0,
            ),
        })

    # ==================================================
    # RM TABLE - EVERY ACTIVE RM
    # ==================================================
    active_rms = User.objects.filter(
        is_active=True,
        role_id=RM_ROLE_ID,
    ).order_by("name")

    rm_table = []

    for rm in active_rms:

        rm_inquiries = inquiries.filter(rm=rm)

        touchbase = rm_inquiries.filter(
            status=Inquiry.Status.TOUCHBASE
        ).count()

        follow_up = rm_inquiries.filter(
            status=Inquiry.Status.TOUCHBASE_FOLLOWUP
        ).count()

        rm_active = rm_inquiries.filter(
            status=Inquiry.Status.ACTIVE_CONVERSATIONS
        ).count()

        nurture = rm_inquiries.filter(
            status=Inquiry.Status.NURTURE
        ).count()

        rm_won = rm_inquiries.filter(
            status=Inquiry.Status.WON
        )

        won_count_rm = rm_won.count()

        lost = rm_inquiries.filter(
            status=Inquiry.Status.LOST
        ).count()

        revenue = (
            rm_won.aggregate(
                total=Sum("value")
            )["total"]
            or 0
        )

        rm_table.append({
            "rm": {
                "id": str(rm.id),
                "name": rm.name,
            },
            "touchbase": touchbase,
            "followUp": follow_up,
            "active": rm_active,
            "nurture": nurture,
            "won": won_count_rm,
            "lost": lost,
            "total": rm_inquiries.count(),
            "revenue": revenue,
        })

    # ==================================================
    # FINAL RESPONSE
    # ==================================================
    return {
        "kpis": {
            "total": total,
            "unassigned": unassigned,
            "active": active,
            "activeConversations": active_conversations,
            "wonCount": won_count,
            "wonRevenue": won_revenue,
            "lostCount": lost_count,
        },
        "bySource": by_source,
        "byType": by_type,
        "trend": trend,
        "rmTable": rm_table,
    }

def get_rm_dashboard(rm, range_days=30):
    now = timezone.now()
    today = timezone.localdate()

    start_date = now - timedelta(days=range_days)

    inquiries = Inquiry.objects.filter(
        rm=rm,
        created_at__gte=start_date,
    )

    # ==============================================
    # TOUCHBASE
    # overdue = follow-up date before today
    # ==============================================
    touchbase_qs = inquiries.filter(
        status=Inquiry.Status.TOUCHBASE
    )

    touchbase_count = touchbase_qs.count()

    touchbase_overdue = touchbase_qs.filter(
        next_follow_up__date__lt=today
    ).count()

    # ==============================================
    # FOLLOW UP
    # ==============================================
    followup_qs = inquiries.filter(
        status=Inquiry.Status.TOUCHBASE_FOLLOWUP
    )

    followup_count = followup_qs.count()

    followup_overdue = followup_qs.filter(
        next_follow_up__date__lt=today
    ).count()

    # ==============================================
    # ACTIVE CONVERSATIONS
    # dueToday = next follow-up is today
    # ==============================================
    active_qs = inquiries.filter(
        status=Inquiry.Status.ACTIVE_CONVERSATIONS
    )

    active_count = active_qs.count()

    active_due_today = active_qs.filter(
        next_follow_up__date=today
    ).count()

    # ==============================================
    # NURTURE
    # ==============================================
    nurture_count = inquiries.filter(
        status=Inquiry.Status.NURTURE
    ).count()

    # ==============================================
    # WON
    # ==============================================
    won_qs = inquiries.filter(
        status=Inquiry.Status.WON
    )

    won_count = won_qs.count()

    won_value = (
        won_qs.aggregate(total=Sum("value"))["total"]
        or 0
    )

    # ==============================================
    # LOST
    # ==============================================
    lost_qs = inquiries.filter(
        status=Inquiry.Status.LOST
    )

    lost_count = lost_qs.count()

    lost_value = (
        lost_qs.aggregate(total=Sum("value"))["total"]
        or 0
    )

    return {
        "kpis": {
            "touchbase": {
                "count": touchbase_count,
                "overdue": touchbase_overdue,
            },
            "followUp": {
                "count": followup_count,
                "overdue": followup_overdue,
            },
            "active": {
                "count": active_count,
                "dueToday": active_due_today,
            },
            "nurture": nurture_count,
            "won": {
                "count": won_count,
                "value": won_value,
            },
            "lost": {
                "count": lost_count,
                "value": lost_value,
            },
        }
    }