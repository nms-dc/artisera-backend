from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone
from decimal import Decimal
from django.db.models import Count, Q, Sum
from accounts.models import User, RM_ROLE_ID
from inquiries.models import Inquiry

ACTIVE_STATUSES = [
    Inquiry.Status.TOUCHBASE,
    Inquiry.Status.TOUCHBASE_FOLLOWUP,
    Inquiry.Status.ACTIVE_CONVERSATIONS,
    Inquiry.Status.NURTURE,
]


# Confirm with the FE what "pipeline" means. Today's sample shows pipelineCount = 0
# while active = 4, so it is probably NOT the same as ACTIVE_STATUSES.
PIPELINE_STATUSES = [Inquiry.Status.ACTIVE_CONVERSATIONS]


def _num(value):
    """Always return a JSON number (never None, never a Decimal string)."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def get_admin_dashboard(range_days=30):
    now = timezone.now()
    start_date = now - timedelta(days=range_days)

    inquiries = Inquiry.objects.filter(created_at__gte=start_date)

    # ---------------- KPIs ----------------
    total = inquiries.count()
    unassigned = inquiries.filter(rm__isnull=True).count()
    active = inquiries.filter(status__in=ACTIVE_STATUSES).count()
    active_conversations = inquiries.filter(
        status=Inquiry.Status.ACTIVE_CONVERSATIONS
    ).count()

    won_inquiries = inquiries.filter(status=Inquiry.Status.WON)
    won_count = won_inquiries.count()
    won_revenue = _num(won_inquiries.aggregate(total=Sum("value"))["total"])

    lost_count = inquiries.filter(status=Inquiry.Status.LOST).count()

    pipeline_qs = inquiries.filter(status__in=PIPELINE_STATUSES)
    pipeline_count = pipeline_qs.count()
    pipeline_value = _num(pipeline_qs.aggregate(total=Sum("value"))["total"])

    # ---------------- BY SOURCE ----------------
    source_counts = dict(
        inquiries.values("source")
        .annotate(count=Count("id"))
        .values_list("source", "count")
    )
    by_source = [
        {"source": source, "count": source_counts.get(source, 0)}
        for source, _ in Inquiry.Source.choices
    ]

    # ---------------- BY TYPE ----------------
    type_counts = dict(
        inquiries.values("inquiry_type")
        .annotate(count=Count("id"))
        .values_list("inquiry_type", "count")
    )
    by_type = [
        {"type": inquiry_type, "count": type_counts.get(inquiry_type, 0)}
        for inquiry_type, _ in Inquiry.InquiryType.choices
    ]

    # ---------------- TREND (13 weeks) ----------------
    trend_start = now - timedelta(weeks=12)
    trend_data = (
        Inquiry.objects.filter(created_at__gte=trend_start)
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(count=Count("id"))
        .order_by("week")
    )
    trend_counts = {item["week"].date(): item["count"] for item in trend_data}

    current_week = now.date() - timedelta(days=now.weekday())
    trend = []
    for weeks_ago in range(12, -1, -1):
        week_start = current_week - timedelta(weeks=weeks_ago)
        trend.append(
            {
                "weekStart": week_start.isoformat(),  # "2026-11-09" (plain date, as the FE sample)
                "count": trend_counts.get(week_start, 0),
            }
        )

    # ---------------- RM TABLE (one grouped query) ----------------
    S = Inquiry.Status
    stats = {
        row["rm"]: row
        for row in (
            inquiries.filter(rm__isnull=False)
            .values("rm")
            .annotate(
                touchbase=Count("id", filter=Q(status=S.TOUCHBASE)),
                follow_up=Count("id", filter=Q(status=S.TOUCHBASE_FOLLOWUP)),
                active=Count("id", filter=Q(status=S.ACTIVE_CONVERSATIONS)),
                nurture=Count("id", filter=Q(status=S.NURTURE)),
                won=Count("id", filter=Q(status=S.WON)),
                lost=Count("id", filter=Q(status=S.LOST)),
                total=Count("id"),
                won_value=Sum("value", filter=Q(status=S.WON)),
                pipeline_value=Sum("value", filter=Q(status__in=PIPELINE_STATUSES)),
            )
        )
    }

    active_rms = User.objects.filter(is_active=True, role_id=RM_ROLE_ID).order_by(
        "name"
    )

    rm_table = []
    for rm in active_rms:
        s = stats.get(rm.id, {})  # RMs with no inquiries still get a row of zeros
        won_value = _num(s.get("won_value"))
        rm_table.append(
            {
                "rm": {"id": str(rm.id), "name": rm.name},
                "touchbase": s.get("touchbase", 0),
                "followUp": s.get("follow_up", 0),
                "active": s.get("active", 0),
                "nurture": s.get("nurture", 0),
                "won": s.get("won", 0),
                "lost": s.get("lost", 0),
                "total": s.get("total", 0),
                "wonValue": won_value,
                "pipelineValue": _num(s.get("pipeline_value")),
                "revenue": won_value,
            }
        )

    return {
        "kpis": {
            "total": total,
            "unassigned": unassigned,
            "active": active,
            "activeConversations": active_conversations,
            "wonCount": won_count,
            "wonRevenue": won_revenue,
            "pipelineCount": pipeline_count,
            "pipelineValue": pipeline_value,
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
    touchbase_qs = inquiries.filter(status=Inquiry.Status.TOUCHBASE)

    touchbase_count = touchbase_qs.count()

    touchbase_overdue = touchbase_qs.filter(next_follow_up__date__lt=today).count()

    # ==============================================
    # FOLLOW UP
    # ==============================================
    followup_qs = inquiries.filter(status=Inquiry.Status.TOUCHBASE_FOLLOWUP)

    followup_count = followup_qs.count()

    followup_overdue = followup_qs.filter(next_follow_up__date__lt=today).count()

    # ==============================================
    # ACTIVE CONVERSATIONS
    # dueToday = next follow-up is today
    # ==============================================
    active_qs = inquiries.filter(status=Inquiry.Status.ACTIVE_CONVERSATIONS)

    active_count = active_qs.count()

    active_due_today = active_qs.filter(next_follow_up__date=today).count()

    # ==============================================
    # NURTURE
    # ==============================================
    nurture_count = inquiries.filter(status=Inquiry.Status.NURTURE).count()

    # ==============================================
    # WON
    # ==============================================
    won_qs = inquiries.filter(status=Inquiry.Status.WON)

    won_count = won_qs.count()

    won_value = won_qs.aggregate(total=Sum("value"))["total"] or 0

    # ==============================================
    # LOST
    # ==============================================
    lost_qs = inquiries.filter(status=Inquiry.Status.LOST)

    lost_count = lost_qs.count()

    lost_value = lost_qs.aggregate(total=Sum("value"))["total"] or 0

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
