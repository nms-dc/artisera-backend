from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import get_inquiry_summary, get_inquiry_detail_report
import csv
from datetime import datetime, time
from django.db.models import Q
from django.http import HttpResponse
from inquiries.models import Inquiry
from django.utils import timezone


class InquirySummaryView(APIView):

    def get(self, request):

        # Permission: reports.view
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.can("reports", "view")
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission to perform this action."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Query parameters
        from_date_value = request.query_params.get("from")
        to_date_value = request.query_params.get("to")

        rm_id = request.query_params.get("rmId")
        category_id = request.query_params.get("categoryId")
        inquiry_status = request.query_params.get("status")

        # Parse dates
        try:
            from_date = (
                datetime.strptime(
                    from_date_value,
                    "%Y-%m-%d"
                ).date()
                if from_date_value
                else None
            )

            to_date = (
                datetime.strptime(
                    to_date_value,
                    "%Y-%m-%d"
                ).date()
                if to_date_value
                else None
            )

        except ValueError:
            return Response(
                {
                    "detail": (
                        "Dates must be in YYYY-MM-DD format."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_inquiry_summary(
            from_date=from_date,
            to_date=to_date,
            rm_id=rm_id,
            category_id=category_id,
            inquiry_status=inquiry_status,
        )

        return Response(data)


class InquiryDetailReportView(APIView):

    def get(self, request):

        # Permission: reports.view
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.can("reports", "view")
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to perform this action."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # ==================================================
        # QUERY PARAMETERS
        # ==================================================

        from_date_value = request.query_params.get("from")
        to_date_value = request.query_params.get("to")

        inquiry_status = request.query_params.get("status")
        q = request.query_params.get("q")

        # Safe pagination
        try:
            page = max(
                int(request.query_params.get("page", 1)),
                1,
            )

            page_size = max(
                int(request.query_params.get("pageSize", 10)),
                1,
            )

        except ValueError:
            return Response(
                {
                    "detail": (
                        "page and pageSize must be integers."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==================================================
        # DATE PARSING
        # ==================================================

        try:
            from_date = (
                datetime.strptime(
                    from_date_value,
                    "%Y-%m-%d"
                ).date()
                if from_date_value
                else None
            )

            to_date = (
                datetime.strptime(
                    to_date_value,
                    "%Y-%m-%d"
                ).date()
                if to_date_value
                else None
            )

        except ValueError:
            return Response(
                {
                    "detail": (
                        "Dates must be in YYYY-MM-DD format."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_inquiry_detail_report(
            from_date=from_date,
            to_date=to_date,
            inquiry_status=inquiry_status,
            q=q,
            page=page,
            page_size=page_size,
        )

        return Response(data)


class InquiryDetailExportView(APIView):

    def get(self, request):

        # Permission: reports.view
        if (
            not request.user
            or not request.user.is_authenticated
            or not request.user.can("reports", "view")
        ):
            return Response(
                {
                    "detail": (
                        "You do not have permission "
                        "to perform this action."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        from_date_value = request.query_params.get("from")
        to_date_value = request.query_params.get("to")
        q = request.query_params.get("q")

        # Parse dates
        try:
            from_date = (
                datetime.strptime(
                    from_date_value,
                    "%Y-%m-%d"
                ).date()
                if from_date_value
                else None
            )

            to_date = (
                datetime.strptime(
                    to_date_value,
                    "%Y-%m-%d"
                ).date()
                if to_date_value
                else None
            )

        except ValueError:
            return Response(
                {
                    "detail": (
                        "Dates must be in YYYY-MM-DD format."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        inquiries = (
            Inquiry.objects
            .select_related(
                "customer",
                "category",
                "subcategory",
                "rm",
            )
            .all()
        )

        # Date filters
        if from_date:
            inquiries = inquiries.filter(
                created_at__gte=timezone.make_aware(
                    datetime.combine(from_date, time.min)
                )
            )

        if to_date:
            inquiries = inquiries.filter(
                created_at__lte=timezone.make_aware(
                    datetime.combine(to_date, time.max)
                )
            )

        # Search
        if q:
            inquiries = inquiries.filter(
                Q(code__icontains=q)
                | Q(customer__name__icontains=q)
                | Q(customer__email__icontains=q)
                | Q(customer__phone__icontains=q)
                | Q(requirement__icontains=q)
            )

        inquiries = inquiries.order_by("-created_at")

        # CSV response
        response = HttpResponse(
            content_type="text/csv"
        )

        response[
            "Content-Disposition"
        ] = 'attachment; filename="inquiry-detail.csv"'

        writer = csv.writer(response)

        writer.writerow([
            "Inquiry ID",
            "Customer",
            "Phone",
            "Email",
            "Category",
            "Subcategory",
            "Quantity",
            "Value",
            "Status",
            "Follow-up Date",
            "RM",
            "Created",
        ])

        for inquiry in inquiries:

            writer.writerow([
                inquiry.code or "",
                inquiry.customer.name,
                inquiry.customer.phone,
                inquiry.customer.email,

                (
                    inquiry.category.name
                    if inquiry.category
                    else ""
                ),

                (
                    inquiry.subcategory.name
                    if inquiry.subcategory
                    else ""
                ),

                inquiry.quantity or "",

                (
                    inquiry.value
                    if inquiry.value is not None
                    else ""
                ),

                inquiry.status,

                (
                    inquiry.next_follow_up.strftime(
                        "%Y-%m-%d"
                    )
                    if inquiry.next_follow_up
                    else ""
                ),

                (
                    inquiry.rm.name
                    if inquiry.rm
                    else "Unassigned"
                ),

                inquiry.created_at.strftime(
                    "%Y-%m-%d"
                ),
            ])

        return response