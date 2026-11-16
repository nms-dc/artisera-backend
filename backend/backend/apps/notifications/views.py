from django.shortcuts import get_object_or_404

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = (
            Notification.objects.filter(user=request.user)
            .select_related("inquiry", "customer")
            .order_by("-created_at")
        )

        unread_count = notifications.filter(is_read=False).count()

        def _id(value):
            return str(value) if value else None

        results = [
            {
                "id": str(n.id),
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "inquiryId": _id(n.inquiry_id),
                "customerId": _id(n.customer_id),
                "saleId": _id(n.sale_id),
                "orderId": _id(n.order_id),
                "tab": n.tab,
                "read": n.is_read,
                "createdAt": n.created_at,
            }
            for n in notifications
        ]

        return Response({"unreadCount": unread_count, "results": results})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])

        return Response({})


class NotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response({})
