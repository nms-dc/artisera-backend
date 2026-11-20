from django.db.models import Count
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import csv
from django.http import HttpResponse
from django.utils import timezone
from inquiries.models import Customer, Sale  # add Customer to your existing import
from .permissions import (  # add scope_customers to your existing import
    require_permission,
    scope_customers,
    scope_orders,
    scope_sales,
)
import datetime as dt
from .models import Order
from .permissions import require_permission, scope_orders, scope_sales
import uuid

from django.db.models import Count, Exists, OuterRef, Q

from inquiries.models import Customer, Sale, SaleProduct
from .serializers import (
    AttentionSaleSerializer,
    OrderListSerializer,
    SaleListSerializer,
)
from .services import (
    CERTIFICATE_PENDING_Q,
    CERTIFICATE_STATUSES,
    DELIVERED_Q,
    ORDER_STATUS_FILTERS,
    ORDER_STATUS_NONE,
    PACKING_Q,
    PREPARATION_Q,
    SALE_PENDING_Q,
    SEPARATE_CERTIFICATE_PLAN,
    SHIPPED_Q,
)
import datetime as dt

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Order, OrderProduct
from .models import SaleLog
from .serializers import SaleProductSerializer, SaleProductUpdateSerializer
from .services import COMMISSION_STATUS

MAX_PAGE_SIZE = 100

ATTENTION_LIMIT = 5


def _parse_date_param(value, name, errors):
    if not value:
        return None
    try:
        parsed = parse_date(value)
    except ValueError:
        parsed = None
    if parsed is None:
        errors[name] = ["Enter a valid date in yyyy-MM-dd format."]
    return parsed


class GalleryDashboardView(APIView):
    """
    GET /api/v1/gallery/dashboard/?from=yyyy-MM-dd&to=yyyy-MM-dd
    Permission: sales.view
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        require_permission(user, "sales", "view")

        errors = {}
        date_from = _parse_date_param(request.query_params.get("from"), "from", errors)
        date_to = _parse_date_param(request.query_params.get("to"), "to", errors)
        if not errors and date_from and date_to and date_from > date_to:
            errors["from"] = ["'from' cannot be after 'to'."]
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        orders = scope_orders(Order.objects.all(), user)

        # ---- Cards: orders created in the range, by derived status ----
        ranged = orders
        if date_from:
            ranged = ranged.filter(created_at__date__gte=date_from)
        if date_to:
            ranged = ranged.filter(created_at__date__lte=date_to)

        cards = ranged.aggregate(
            preparation=Count("id", filter=PREPARATION_Q),
            packingDispatch=Count("id", filter=PACKING_Q),
            shipped=Count("id", filter=SHIPPED_Q),
            delivered=Count("id", filter=DELIVERED_Q),
            certificatesPending=Count("id", filter=CERTIFICATE_PENDING_Q),
        )

        # ---- Attention orders: not Delivered, newest first ----
        attention_orders = orders.exclude(DELIVERED_Q)
        attention_orders_top = (
            attention_orders.select_related(
                "sale__inquiry__customer", "sale__inquiry__rm"
            )
            .prefetch_related("order_products__sale_product")
            .order_by("-created_at")[:ATTENTION_LIMIT]
        )

        # ---- Attention sales: has a pendingWith reason, newest first ----
        attention_sales = scope_sales(Sale.objects.all(), user).filter(SALE_PENDING_Q)
        attention_sales_top = attention_sales.select_related(
            "inquiry__customer", "inquiry__rm", "email_status"
        ).order_by("-sale_date", "-created_at")[:ATTENTION_LIMIT]

        return Response(
            {
                "cards": cards,
                "attentionOrders": {
                    "count": attention_orders.count(),
                    "results": OrderListSerializer(
                        attention_orders_top, many=True
                    ).data,
                },
                "attentionSales": {
                    "count": attention_sales.count(),
                    "results": AttentionSaleSerializer(
                        attention_sales_top, many=True
                    ).data,
                },
            }
        )


class GalleryCustomerOptionsView(APIView):
    """
    GET /api/v1/gallery/customers/
    Permission: orders.view
    Plain array of {id, name} for customers who have sales.
    An RM sees only customers of their own sales.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        require_permission(user, "orders", "view")

        customers = (
            scope_customers(Customer.objects.all(), user)
            .only("id", "name")
            .order_by("name")
        )

        return Response([{"id": str(c.id), "name": c.name} for c in customers])


class GallerySaleListView(APIView):
    """
    GET /api/v1/gallery/sales/
    Params: from, to, customerId, q, orderStatus, certificateStatus, page, pageSize
    Permission: sales.view
    """

    permission_classes = [IsAuthenticated]

    def filtered_sales(self, request):
        """Returns (queryset, None) or (None, error_response)."""
        user = request.user
        params = request.query_params
        errors = {}

        date_from = _parse_date_param(params.get("from"), "from", errors)
        date_to = _parse_date_param(params.get("to"), "to", errors)
        if not errors and date_from and date_to and date_from > date_to:
            errors["from"] = ["'from' cannot be after 'to'."]

        customer_id = params.get("customerId")
        if customer_id:
            try:
                customer_id = uuid.UUID(customer_id)
            except ValueError:
                errors["customerId"] = ["Enter a valid UUID."]

        order_status = params.get("orderStatus")
        if (
            order_status
            and order_status != ORDER_STATUS_NONE
            and order_status not in ORDER_STATUS_FILTERS
        ):
            errors["orderStatus"] = [
                "Must be one of: "
                + ", ".join([*ORDER_STATUS_FILTERS, ORDER_STATUS_NONE])
                + "."
            ]

        certificate_status = params.get("certificateStatus")
        if certificate_status and certificate_status not in CERTIFICATE_STATUSES:
            errors["certificateStatus"] = [
                "Must be one of: " + ", ".join(CERTIFICATE_STATUSES) + "."
            ]

        if errors:
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        queryset = scope_sales(Sale.objects.all(), user)

        if date_from:
            queryset = queryset.filter(sale_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(sale_date__date__lte=date_to)

        if customer_id:
            queryset = queryset.filter(inquiry__customer_id=customer_id)

        q = (params.get("q") or "").strip()
        if q:
            product_match = SaleProduct.objects.filter(sale=OuterRef("pk")).filter(
                Q(name__icontains=q) | Q(artist__name__icontains=q)
            )
            queryset = queryset.annotate(_product_match=Exists(product_match)).filter(
                Q(code__icontains=q)
                | Q(inquiry__code__icontains=q)
                | Q(inquiry__customer__name__icontains=q)
                | Q(_product_match=True)
            )

        sale_orders = Order.objects.filter(sale=OuterRef("pk"))
        if order_status == ORDER_STATUS_NONE:
            queryset = queryset.annotate(_has_orders=Exists(sale_orders)).filter(
                _has_orders=False
            )
        elif order_status:
            queryset = queryset.annotate(
                _status_match=Exists(
                    sale_orders.filter(ORDER_STATUS_FILTERS[order_status])
                )
            ).filter(_status_match=True)

        if certificate_status:
            separate = Q(certificate_plan=SEPARATE_CERTIFICATE_PLAN)
            if certificate_status == "with-shipment":
                queryset = queryset.exclude(separate)
            else:
                queryset = queryset.annotate(
                    _any_orders=Exists(sale_orders),
                    _any_unsent=Exists(
                        sale_orders.filter(certificate_sent_at__isnull=True)
                    ),
                ).filter(separate)
                if certificate_status == "pending":
                    queryset = queryset.filter(
                        Q(_any_orders=False) | Q(_any_unsent=True)
                    )
                else:
                    queryset = queryset.filter(_any_orders=True, _any_unsent=False)

        queryset = (
            queryset.select_related("inquiry__customer", "inquiry__rm", "email_status")
            .prefetch_related("products", "orders__order_products")
            .order_by("-sale_date", "-created_at", "-id")
        )
        return queryset, None

    def get(self, request):
        require_permission(request.user, "sales", "view")

        queryset, error = self.filtered_sales(request)
        if error:
            return error

        params = request.query_params

        def _int(name, default, maximum=None):
            try:
                value = max(int(params.get(name, default)), 1)
            except (TypeError, ValueError):
                return default
            return min(value, maximum) if maximum else value

        page = _int("page", 1)
        page_size = _int("pageSize", 10, maximum=MAX_PAGE_SIZE)

        count = queryset.count()
        start = (page - 1) * page_size
        items = queryset[start : start + page_size]

        return Response(
            {
                "count": count,
                "page": page,
                "pageSize": page_size,
                "results": SaleListSerializer(items, many=True).data,
            }
        )


def _csv_safe(value):
    """Stop spreadsheet apps from running user text as a formula."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


class GallerySaleExportView(GallerySaleListView):
    """
    GET /api/v1/gallery/sales/export/
    Same filters as the list (page and pageSize are ignored); returns every match.
    Permission: sales.view
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_permission(request.user, "sales", "view")

        queryset, error = self.filtered_sales(request)
        if error:
            return error

        sales = list(queryset)
        rows = SaleListSerializer(sales, many=True).data

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="sales-{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("\ufeff")  # BOM so Excel reads UTF-8 correctly

        writer = csv.writer(response)
        writer.writerow(
            [
                "Sale Number",
                "Customer",
                "Sale Date",
                "Total Sale Value",
                "Total Orders",
                "Total Products",
                "Products Remaining",
                "Certificate Sent Separately",
            ]
        )
        for sale, row in zip(sales, rows):
            writer.writerow(
                [
                    _csv_safe(row["saleNumber"]),
                    _csv_safe(row["customer"]["name"]),
                    timezone.localtime(sale.sale_date).strftime("%Y-%m-%d"),
                    row["totalValue"],
                    row["totalOrders"],
                    row["totalProducts"],
                    row["productsRemaining"],
                    "Yes" if row["certificateSeparately"] else "No",
                ]
            )
        return response


class GallerySaleProductView(APIView):
    """
    PATCH /api/v1/gallery/sales/{id}/products/{productId}/
    Body: productStatus?, commissionReadyDate?, orderNotes?
    Permission: sales.edit
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, product_id):
        user = request.user
        require_permission(user, "sales", "edit")

        serializer = SaleProductUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sale = get_object_or_404(scope_sales(Sale.objects.all(), user), pk=pk)

        with transaction.atomic():
            product = get_object_or_404(
                SaleProduct.objects.select_for_update(), pk=product_id, sale=sale
            )

            if OrderProduct.objects.filter(sale_product=product).exists():
                return Response(
                    {"detail": "This product is already in an order."},
                    status=status.HTTP_409_CONFLICT,
                )

            new_status = data.get("productStatus", product.product_status)

            if "commissionReadyDate" in data:
                ready = data["commissionReadyDate"]
                new_ready = (
                    dt.datetime.combine(ready, dt.time.min, tzinfo=dt.timezone.utc)
                    if ready
                    else None
                )
            else:
                new_ready = product.commission_ready_date

            if new_status == COMMISSION_STATUS and new_ready is None:
                return Response(
                    {
                        "commissionReadyDate": [
                            "This field is required when the status is Commission."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            changes = []

            if new_status != product.product_status:
                changes.append(f"status {product.product_status or '-'} → {new_status}")
                product.product_status = new_status

            if new_ready != product.commission_ready_date:
                changes.append(
                    "commission ready date "
                    + (new_ready.date().isoformat() if new_ready else "cleared")
                )
                product.commission_ready_date = new_ready

            if "orderNotes" in data:
                new_notes = data["orderNotes"] or ""
                if new_notes != product.order_notes:
                    changes.append("order notes updated")
                    product.order_notes = new_notes

            if changes:
                product.save()
                SaleLog.objects.create(
                    sale=sale,
                    title="Product Updated",
                    text=f"{product.name}: " + "; ".join(changes),
                    created_by=user,
                )

        product = SaleProduct.objects.select_related(
            "artist", "order_product__order"
        ).get(pk=product.pk)
        return Response(SaleProductSerializer(product).data)
