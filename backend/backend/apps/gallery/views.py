from django.db.models import Count
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import csv
import os
from django.http import HttpResponse
from django.utils import timezone
from inquiries.models import (
    Customer,
    Sale,
    SaleProduct,
)  # add Customer to your existing import
from .permissions import (  # add scope_customers to your existing import
    require_permission,
    scope_customers,
    scope_orders,
    scope_sales,
    can_access_order,
)
import datetime as dt
from .models import (
    Order,
    OrderLog,
    OrderMedia,
    OrderProduct,
    Package,
    SaleEmailStatus,
    SaleLog,
)
from .permissions import require_permission, scope_orders, scope_sales
import uuid
from .models import Order, OrderProduct, SaleEmailStatus, SaleLog
from django.db.models import (
    Count,
    Exists,
    OuterRef,
    Q,
    Case,
    DateTimeField,
    F,
    Value,
    When,
)
from inquiries.models import Customer, Sale, SaleProduct
from .serializers import (
    AttentionSaleSerializer,
    OrderListSerializer,
    SaleListSerializer,
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderSaveSerializer,
    LogEntrySerializer,
    ALLOWED_MEDIA_TYPES,
    OrderMediaUploadSerializer,
    serialize_media,
    OrderDispatchSerializer,
    OrderReceivedSerializer,
    OrderCertificateSentSerializer,
    ShipmentRowSerializer,
    ShipmentStatusSerializer,
    CertificateRowSerializer,
    SaleDetailSerializer,
)
from rest_framework.parsers import FormParser, MultiPartParser
from .models import Order, OrderLog, OrderMedia, OrderProduct, SaleEmailStatus, SaleLog

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
    IN_STOCK_STATUS,
    notify_gallery_managers,
    order_suffix,
    sale_email_confirmed,
    ORDER_LIST_STATUS_FILTERS,
    SHIPMENT_STATUSES,
)
import datetime as dt

from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Order, OrderProduct
from .models import SaleLog
from .serializers import SaleProductSerializer, SaleProductUpdateSerializer
from .services import COMMISSION_STATUS
from rest_framework.exceptions import PermissionDenied
from .services import notify_gallery_managers  # add to your existing .services import
from accounts.models import RM_ROLE_ID

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


class GallerySaleEmailOverrideView(APIView):
    """
    POST /api/v1/gallery/sales/{id}/email-override/
    Body: {}
    Marks the RM email as received (overridden). Permission: sales.edit
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        require_permission(user, "sales", "edit")

        sale = get_object_or_404(scope_sales(Sale.objects.all(), user), pk=pk)

        with transaction.atomic():
            email_status, _ = SaleEmailStatus.objects.select_for_update().get_or_create(
                sale=sale
            )

            if email_status.received_at is not None:
                return Response(
                    {"detail": "The RM email has already been received."},
                    status=status.HTTP_409_CONFLICT,
                )

            email_status.received_at = timezone.now()
            email_status.overridden = True
            email_status.save()

            SaleLog.objects.create(
                sale=sale,
                title="RM Email Override",
                text="RM email marked as received by override.",
                created_by=user,
            )

        return Response({"id": str(sale.id), "emailConfirmed": True})


class _SaleEmailReceiveBase(APIView):
    """
    Shared logic for the two ways the RM email is marked received.
    Subclasses set `overridden`, `log_title` and `log_text`.
    Permission: sales.edit
    """

    permission_classes = [IsAuthenticated]
    overridden = False
    log_title = ""
    log_text = ""

    def post(self, request, pk):
        user = request.user
        require_permission(user, "sales", "edit")

        sale = get_object_or_404(scope_sales(Sale.objects.all(), user), pk=pk)

        with transaction.atomic():
            email_status, _ = SaleEmailStatus.objects.select_for_update().get_or_create(
                sale=sale
            )

            if email_status.received_at is not None:
                return Response(
                    {"detail": "The RM email has already been received."},
                    status=status.HTTP_409_CONFLICT,
                )

            email_status.received_at = timezone.now()
            email_status.overridden = self.overridden
            email_status.save()

            SaleLog.objects.create(
                sale=sale,
                title=self.log_title,
                text=self.log_text,
                created_by=user,
            )

        return Response({"id": str(sale.id), "emailConfirmed": True})


class GallerySaleEmailOverrideView(_SaleEmailReceiveBase):
    """POST /api/v1/gallery/sales/{id}/email-override/"""

    overridden = True
    log_title = "RM Email Override"
    log_text = "RM email marked as received by override."


class GallerySaleEmailReceivedView(_SaleEmailReceiveBase):
    """POST /api/v1/gallery/sales/{id}/email-received/"""

    overridden = False
    log_title = "RM Email Received"
    log_text = "RM email marked as received."


class GallerySaleEmailSentView(APIView):
    """
    POST /api/v1/gallery/sales/{id}/email-sent/
    Body: {}
    The sale's RM (or an Admin) marks the email as sent to the gallery.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        sale = get_object_or_404(Sale.objects.select_related("inquiry"), pk=pk)

        # Only the sale's own RM or an Admin; everyone else gets 403.
        if not (user.is_admin or sale.inquiry.rm_id == user.id):
            raise PermissionDenied("You do not have permission to do this.")

        with transaction.atomic():
            email_status, _ = SaleEmailStatus.objects.select_for_update().get_or_create(
                sale=sale
            )

            if email_status.received_at is not None:
                return Response(
                    {"detail": "The RM email has already been received."},
                    status=status.HTTP_409_CONFLICT,
                )
            if email_status.rm_email_sent_at is not None:
                return Response(
                    {"detail": "The email has already been marked as sent."},
                    status=status.HTTP_409_CONFLICT,
                )

            email_status.rm_email_sent_at = timezone.now()
            email_status.save()

            SaleLog.objects.create(
                sale=sale,
                title="RM Email Sent",
                text="RM marked the email as sent to the gallery.",
                created_by=user,
            )

            # Notify only after the change is committed.
            transaction.on_commit(
                lambda: notify_gallery_managers(
                    "SALE_EMAIL_SENT",
                    title="RM email sent",
                    text=f"The RM has sent the email for sale {sale.code}.",
                    sale=sale,
                    actor=user,
                )
            )

        return Response({"id": str(sale.id)})


class GallerySaleOrderCreateView(APIView):
    """
    POST /api/v1/gallery/sales/{id}/orders/
    Body: {"groups": [[productId, ...], ...]}  -> one order per group
    Permission: orders.create
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        require_permission(user, "orders", "create")

        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        groups = serializer.validated_data["groups"]
        requested_ids = [pid for group in groups for pid in group]

        sale = get_object_or_404(scope_sales(Sale.objects.all(), user), pk=pk)

        with transaction.atomic():
            # Serialise concurrent order creation for the same sale.
            Sale.objects.select_for_update().get(pk=sale.pk)

            if not sale_email_confirmed(sale):
                return Response(
                    {"detail": "The RM email has not been received yet."},
                    status=status.HTTP_409_CONFLICT,
                )

            products = {
                p.id: p
                for p in SaleProduct.objects.filter(sale=sale, pk__in=requested_ids)
            }
            missing = [str(i) for i in requested_ids if i not in products]
            if missing:
                return Response(
                    {
                        "groups": [
                            "Products not found in this sale: " + ", ".join(missing)
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if OrderProduct.objects.filter(sale_product_id__in=requested_ids).exists():
                return Response(
                    {"detail": "One or more products are already in an order."},
                    status=status.HTTP_409_CONFLICT,
                )

            not_in_stock = [
                p.name for p in products.values() if p.product_status != IN_STOCK_STATUS
            ]
            if not_in_stock:
                return Response(
                    {"groups": ["Products not In Stock: " + ", ".join(not_in_stock)]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---- Order numbering ----
            all_product_ids = set(
                SaleProduct.objects.filter(sale=sale).values_list("id", flat=True)
            )
            one_order_holds_everything = (
                len(groups) == 1 and set(groups[0]) == all_product_ids
            )
            suffix_index = Order.objects.filter(sale=sale).count()
            certificate_included = sale.certificate_plan != SEPARATE_CERTIFICATE_PLAN

            orders = []
            for group in groups:
                if one_order_holds_everything:
                    number = sale.code
                else:
                    number = f"{sale.code}-{order_suffix(suffix_index)}"
                    while Order.objects.filter(order_number=number).exists():
                        suffix_index += 1
                        number = f"{sale.code}-{order_suffix(suffix_index)}"
                    suffix_index += 1

                order = Order.objects.create(
                    sale=sale,
                    order_number=number,
                    certificate_included=certificate_included,
                    created_by=user,
                )
                OrderProduct.objects.bulk_create(
                    [
                        OrderProduct(order=order, sale_product=products[pid])
                        for pid in group
                    ]
                )
                OrderLog.objects.create(
                    order=order,
                    title="Order Created",
                    text=f"Order {number} created with {len(group)} product(s).",
                    created_by=user,
                )
                orders.append(order)

            SaleLog.objects.create(
                sale=sale,
                title="Orders Created",
                text="Created: " + ", ".join(o.order_number for o in orders),
                created_by=user,
            )

            for order in orders:
                transaction.on_commit(
                    lambda o=order: notify_gallery_managers(
                        "ORDER_CREATED",
                        title="Order created",
                        text=f"Order {o.order_number} was created for sale {sale.code}.",
                        sale=sale,
                        order=o,
                        actor=user,
                    )
                )

        fetched = {
            o.pk: o
            for o in Order.objects.filter(pk__in=[o.pk for o in orders])
            .select_related("sale__inquiry__customer", "sale__inquiry__rm")
            .prefetch_related(
                "order_products__sale_product__artist", "packages", "media"
            )
        }
        ordered = [fetched[o.pk] for o in orders]

        return Response(
            OrderDetailSerializer(
                ordered, many=True, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class GalleryOrderListView(APIView):
    """
    GET /api/v1/gallery/orders/
    Params: from, to (order date), customerId, q, status, page, pageSize
    Permission: orders.view
    """

    permission_classes = [IsAuthenticated]

    def filtered_orders(self, request):
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

        status_value = params.get("status")
        if status_value and status_value not in ORDER_LIST_STATUS_FILTERS:
            errors["status"] = [
                "Must be one of: " + ", ".join(ORDER_LIST_STATUS_FILTERS) + "."
            ]

        if errors:
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        queryset = scope_orders(Order.objects.all(), user)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        if customer_id:
            queryset = queryset.filter(sale__inquiry__customer_id=customer_id)

        if status_value:
            queryset = queryset.filter(ORDER_LIST_STATUS_FILTERS[status_value])

        q = (params.get("q") or "").strip()
        if q:
            product_match = OrderProduct.objects.filter(
                order=OuterRef("pk"), sale_product__name__icontains=q
            )
            queryset = queryset.annotate(_product_match=Exists(product_match)).filter(
                Q(order_number__icontains=q)
                | Q(sale__code__icontains=q)
                | Q(sale__inquiry__customer__name__icontains=q)
                | Q(_product_match=True)
            )

        queryset = (
            queryset.select_related("sale__inquiry__customer", "sale__inquiry__rm")
            .prefetch_related("order_products__sale_product")
            .order_by("-created_at", "-id")
        )
        return queryset, None

    def get(self, request):
        require_permission(request.user, "orders", "view")

        queryset, error = self.filtered_orders(request)
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
                "results": OrderListSerializer(items, many=True).data,
            }
        )


# ====================export order view =====================
class GalleryOrderExportView(GalleryOrderListView):
    """
    GET /api/v1/gallery/orders/export/
    Same filters as the list (page and pageSize are ignored); returns every match.
    Permission: orders.view
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_permission(request.user, "orders", "view")

        queryset, error = self.filtered_orders(request)
        if error:
            return error

        orders = list(queryset)
        rows = OrderListSerializer(orders, many=True).data

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="orders-{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("\ufeff")  # BOM so Excel reads UTF-8 correctly

        writer = csv.writer(response)
        writer.writerow(
            [
                "Order Number",
                "Sale Number",
                "Customer",
                "Relationship Manager",
                "Order Date",
                "Total Products",
                "Order Value",
                "Status",
            ]
        )
        for order, row in zip(orders, rows):
            writer.writerow(
                [
                    _csv_safe(row["orderNumber"]),
                    _csv_safe(row["saleNumber"]),
                    _csv_safe(row["customer"]["name"]),
                    _csv_safe(row["rm"]["name"] if row["rm"] else ""),
                    timezone.localtime(order.created_at).strftime("%Y-%m-%d"),
                    row["totalProducts"],
                    row["orderValue"],
                    _csv_safe(row["status"]),
                ]
            )
        return response


# ===============================single gallery order view======================
def load_order_for(user, pk):
    """Fetch an order with everything the detail serializer needs; 404 if unknown, 403 if the RM doesn't own it."""
    order = get_object_or_404(
        Order.objects.select_related(
            "sale__inquiry__customer", "sale__inquiry__rm"
        ).prefetch_related(
            "order_products__sale_product__artist",
            "order_products__sale_product__order_product__order",
            "packages",
            "media",
        ),
        pk=pk,
    )
    if not can_access_order(user, order):
        raise PermissionDenied("You do not have permission to do this.")
    return order


class GalleryOrderDetailView(APIView):
    """
    GET /api/v1/gallery/orders/{id}/
    Permission: orders.view (an RM only for orders of their own sales)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        require_permission(request.user, "orders", "view")
        order = load_order_for(request.user, pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)

    def patch(self, request, pk):
        user = request.user
        require_permission(user, "orders", "edit")

        serializer = OrderSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 404 if unknown, 403 if an RM doesn't own the sale.
        load_order_for(user, pk)

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=pk)

            if order.ready_for_packing:
                return Response(
                    {"detail": "The order is already ready for packing."},
                    status=status.HTTP_409_CONFLICT,
                )

            order_products = {
                op.sale_product_id: op for op in order.order_products.all()
            }

            updates = data.get("products", [])
            unknown = [str(i["id"]) for i in updates if i["id"] not in order_products]
            if unknown:
                return Response(
                    {"products": ["Not in this order: " + ", ".join(unknown)]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            changed = False
            for item in updates:
                op = order_products[item["id"]]
                if op.photo_video_uploaded != item["photoVideoUploaded"]:
                    op.photo_video_uploaded = item["photoVideoUploaded"]
                    op.save(update_fields=["photo_video_uploaded"])
                    changed = True

            mark_ready = data.get("readyForPacking") is True
            if mark_ready:
                missing = [
                    op.sale_product.name
                    for op in order_products.values()
                    if not op.photo_video_uploaded
                ]
                if missing:
                    transaction.set_rollback(True)  # discard the flag updates above
                    return Response(
                        {
                            "readyForPacking": [
                                "Photos/videos must be uploaded for every product: "
                                + ", ".join(missing)
                            ]
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                order.ready_for_packing = True
                order.save(update_fields=["ready_for_packing", "updated_at"])

            if mark_ready:
                OrderLog.objects.create(
                    order=order,
                    title="Ready for Packing",
                    text=f"Order {order.order_number} marked ready for packing.",
                    created_by=user,
                )
            elif changed:
                OrderLog.objects.create(
                    order=order,
                    title="Order Saved",
                    text=f"Order {order.order_number} saved.",
                    created_by=user,
                )

        order = load_order_for(user, pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class GalleryOrderActivitiesView(APIView):
    """
    GET /api/v1/gallery/orders/{id}/activities/
    Plain array of log entries, oldest first. Permission: orders.view
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        require_permission(user, "orders", "view")

        order = load_order_for(
            user, pk
        )  # 404 unknown, 403 for an RM who doesn't own it

        logs = order.logs.select_related("created_by").order_by("created_at", "id")
        return Response(LogEntrySerializer(logs, many=True).data)


class GalleryOrderMediaUploadView(APIView):
    """
    POST /api/v1/gallery/orders/{id}/media/   (multipart: file, kind)
    Allowed at any order stage. Permission: orders.edit
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        user = request.user
        require_permission(user, "orders", "edit")

        order = load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        serializer = OrderMediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        kind = serializer.validated_data["kind"]

        media_type, _ = ALLOWED_MEDIA_TYPES[upload.content_type.lower()]

        with transaction.atomic():
            media = OrderMedia.objects.create(
                order=order,
                kind=kind,
                type=media_type,
                file=upload,
                file_name=os.path.basename(upload.name)[:255],
                size=upload.size,
                uploaded_by=user,
            )
            OrderLog.objects.create(
                order=order,
                title="Media Uploaded",
                text=f"{media.file_name} ({media.kind}) uploaded.",
                created_by=user,
            )

        return Response(serialize_media(media, request), status=status.HTTP_201_CREATED)


class GalleryOrderMediaDeleteView(APIView):
    """
    DELETE /api/v1/gallery/orders/{id}/media/{mediaId}/
    Response: {}. Permission: orders.edit
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, media_id):
        user = request.user
        require_permission(user, "orders", "edit")

        order = load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        with transaction.atomic():
            media = get_object_or_404(OrderMedia, pk=media_id, order=order)
            file_name = media.file_name
            stored_file = media.file

            media.delete()

            OrderLog.objects.create(
                order=order,
                title="Media Removed",
                text=f"{file_name} removed.",
                created_by=user,
            )

            # Remove the file from disk only once the change is committed.
            transaction.on_commit(lambda: stored_file.delete(save=False))

        return Response({})


class GalleryOrderDispatchView(APIView):
    """
    PATCH /api/v1/gallery/orders/{id}/dispatch/
    Body (either part or both): packages[], courier, waybill, actualDispatchDate,
    certificateIncluded, invoiceIncluded.    Permission: orders.edit
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = request.user
        require_permission(user, "orders", "edit")

        serializer = OrderDispatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=pk)

            if not order.ready_for_packing:
                return Response(
                    {"detail": "The order is not ready for packing yet."},
                    status=status.HTTP_409_CONFLICT,
                )
            if order.actual_dispatch_date is not None:
                return Response(
                    {"detail": "The order has already been dispatched."},
                    status=status.HTTP_409_CONFLICT,
                )

            logs = []

            # ---- Packing part ----
            if "packages" in data:
                existing = {p.id: p for p in order.packages.all()}
                keep_ids = set()
                for item in data["packages"]:
                    package = existing.get(item.get("id")) or Package(order=order)
                    package.packaging_type = item["packagingType"]
                    package.length_cm = item.get("lengthCm")
                    package.width_cm = item.get("widthCm")
                    package.height_cm = item.get("heightCm")
                    package.weight_kg = item.get("weightKg")
                    package.notes = item.get("notes", "")
                    package.save()
                    keep_ids.add(package.id)
                order.packages.exclude(id__in=keep_ids).delete()
                logs.append(("Packing Saved", f"{len(keep_ids)} package(s) saved."))

            # ---- Shipment part ----
            shipment_fields = ("courier", "waybill", "actualDispatchDate")
            if any(f in data for f in shipment_fields):
                courier = data.get("courier") or order.courier
                if not courier:
                    return Response(
                        {"courier": ["This field is required."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                order.courier = courier
                if "waybill" in data:
                    order.waybill = data["waybill"]

                dispatch_date = data.get("actualDispatchDate")
                if dispatch_date:
                    if not order.packages.exists():
                        transaction.set_rollback(True)
                        return Response(
                            {
                                "actualDispatchDate": [
                                    "Save at least one package before dispatching."
                                ]
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    now = timezone.now()
                    order.actual_dispatch_date = dt.datetime.combine(
                        dispatch_date, dt.time.min, tzinfo=dt.timezone.utc
                    )
                    order.shipment_status = "In Transit"
                    order.shipment_status_updated_at = now
                    logs.append(
                        (
                            "Shipment Saved",
                            f"Courier {courier}"
                            + (f", waybill {order.waybill}" if order.waybill else "")
                            + ".",
                        )
                    )
                    logs.append(
                        (
                            "Order Dispatched",
                            f"Order {order.order_number} dispatched on {dispatch_date}.",
                        )
                    )
                else:
                    logs.append(("Shipment Saved", f"Courier {courier}."))

            # ---- Flags ----
            if "certificateIncluded" in data:
                order.certificate_included = data["certificateIncluded"]
            if "invoiceIncluded" in data:
                order.invoice_included = data["invoiceIncluded"]

            order.save()

            for title, text in logs:
                OrderLog.objects.create(
                    order=order, title=title, text=text, created_by=user
                )

            if order.actual_dispatch_date:
                transaction.on_commit(
                    lambda: notify_gallery_managers(
                        "ORDER_SHIPPED",
                        title="Order shipped",
                        text=f"Order {order.order_number} has been shipped.",
                        sale=order.sale,
                        order=order,
                        actor=user,
                    )
                )

        order = load_order_for(user, pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class GalleryOrderReceivedView(APIView):
    """
    POST /api/v1/gallery/orders/{id}/received/
    Body: {"received": true|false, "date": "yyyy-MM-dd"?}
    Permission: orders.edit
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        require_permission(user, "orders", "edit")

        serializer = OrderReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=pk)

            if order.actual_dispatch_date is None:
                return Response(
                    {"detail": "The order has not been dispatched yet."},
                    status=status.HTTP_409_CONFLICT,
                )

            now = timezone.now()

            if data["received"]:
                date = data.get("date")
                if date:
                    if date < order.actual_dispatch_date.date():
                        return Response(
                            {"date": ["The date cannot be before the dispatch date."]},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    received_at = dt.datetime.combine(
                        date, dt.time.min, tzinfo=dt.timezone.utc
                    )
                else:
                    received_at = now

                order.received_at = received_at
                order.shipment_status = "Delivered"
                title = "Order Delivered"
                text = f"Order {order.order_number} marked as received."
            else:
                order.received_at = None
                order.shipment_status = "In Transit"
                title = "Delivery Reverted"
                text = f"Order {order.order_number} set back to In Transit."

            order.shipment_status_updated_at = now
            order.save()

            OrderLog.objects.create(
                order=order, title=title, text=text, created_by=user
            )

            if data["received"]:
                transaction.on_commit(
                    lambda: notify_gallery_managers(
                        "ORDER_DELIVERED",
                        title="Order delivered",
                        text=f"Order {order.order_number} has been delivered.",
                        sale=order.sale,
                        order=order,
                        actor=user,
                    )
                )

        order = load_order_for(user, pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class GalleryOrderCertificateSentView(APIView):
    """
    POST /api/v1/gallery/orders/{id}/certificate-sent/
    Body: {"sent": true|false, "date": "yyyy-MM-dd"?}
    Permission: certificates.edit
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        require_permission(user, "certificates", "edit")

        serializer = OrderCertificateSentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        with transaction.atomic():
            order = Order.objects.select_for_update().select_related("sale").get(pk=pk)

            if order.sale.certificate_plan != SEPARATE_CERTIFICATE_PLAN:
                return Response(
                    {"detail": "This sale sends certificates with the shipment."},
                    status=status.HTTP_409_CONFLICT,
                )

            if data["sent"]:
                date = data.get("date")
                order.certificate_sent_at = (
                    dt.datetime.combine(date, dt.time.min, tzinfo=dt.timezone.utc)
                    if date
                    else timezone.now()
                )
                title = "Certificate Sent"
                text = f"Certificate for order {order.order_number} marked as sent."
            else:
                order.certificate_sent_at = None
                title = "Certificate Send Reverted"
                text = f"Certificate for order {order.order_number} marked as not sent."

            order.save()

            OrderLog.objects.create(
                order=order, title=title, text=text, created_by=user
            )

            if data["sent"]:
                transaction.on_commit(
                    lambda: notify_gallery_managers(
                        "CERTIFICATE_SENT",
                        title="Certificate sent",
                        text=f"The certificate for order {order.order_number} has been sent.",
                        sale=order.sale,
                        order=order,
                        actor=user,
                    )
                )

        order = load_order_for(user, pk)
        return Response(OrderDetailSerializer(order, context={"request": request}).data)


class GalleryShipmentListView(APIView):
    """
    GET /api/v1/gallery/shipments/
    Params: from, to (dispatch date), customerId, q, courier, status, page, pageSize
    Only dispatched orders, newest dispatch first. Permission: shipments.view
    """

    permission_classes = [IsAuthenticated]

    def filtered_shipments(self, request):
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

        status_value = params.get("status")
        if status_value and status_value not in SHIPMENT_STATUSES:
            errors["status"] = ["Must be one of: " + ", ".join(SHIPMENT_STATUSES) + "."]

        if errors:
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        queryset = scope_orders(
            Order.objects.filter(actual_dispatch_date__isnull=False), user
        )

        if date_from:
            queryset = queryset.filter(actual_dispatch_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(actual_dispatch_date__date__lte=date_to)

        if customer_id:
            queryset = queryset.filter(sale__inquiry__customer_id=customer_id)

        courier = (params.get("courier") or "").strip()
        if courier:
            queryset = queryset.filter(courier__iexact=courier)

        if status_value:
            queryset = queryset.filter(shipment_status=status_value)

        q = (params.get("q") or "").strip()
        if q:
            queryset = queryset.filter(
                Q(order_number__icontains=q)
                | Q(sale__code__icontains=q)
                | Q(sale__inquiry__customer__name__icontains=q)
                | Q(waybill__icontains=q)
            )

        queryset = queryset.select_related(
            "sale__inquiry__customer", "sale__inquiry__rm"
        ).order_by("-actual_dispatch_date", "-created_at", "-id")
        return queryset, None

    def get(self, request):
        require_permission(request.user, "shipments", "view")

        queryset, error = self.filtered_shipments(request)
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
                "results": ShipmentRowSerializer(items, many=True).data,
            }
        )


class GalleryShipmentExportView(GalleryShipmentListView):
    """
    GET /api/v1/gallery/shipments/export/
    Same filters as the list (page and pageSize are ignored); returns every match.
    Permission: shipments.view
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_permission(request.user, "shipments", "view")

        queryset, error = self.filtered_shipments(request)
        if error:
            return error

        orders = list(queryset)
        rows = ShipmentRowSerializer(orders, many=True).data

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="shipments-{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("\ufeff")  # BOM so Excel reads UTF-8 correctly

        writer = csv.writer(response)
        writer.writerow(
            [
                "Order Number",
                "Sale Number",
                "Customer",
                "Courier",
                "Tracking No",
                "Dispatch Date",
                "Status",
            ]
        )
        for order, row in zip(orders, rows):
            writer.writerow(
                [
                    _csv_safe(row["orderNumber"]),
                    _csv_safe(row["saleNumber"]),
                    _csv_safe(row["customerName"]),
                    _csv_safe(row["courier"]),
                    _csv_safe(row["trackingNo"]),
                    timezone.localtime(order.actual_dispatch_date).strftime("%Y-%m-%d"),
                    _csv_safe(row["status"]),
                ]
            )
        return response


class GalleryShipmentStatusView(APIView):
    """
    PATCH /api/v1/gallery/shipments/{id}/status/     (id = order id)
    Body: {"status": "In Transit" | "Delivered"}
    Permission: shipments.edit
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        user = request.user
        require_permission(user, "shipments", "edit")

        serializer = ShipmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        load_order_for(user, pk)  # 404 unknown, 403 for a non-owner RM

        with transaction.atomic():
            order = Order.objects.select_for_update().select_related("sale").get(pk=pk)

            if order.actual_dispatch_date is None:
                return Response(
                    {"detail": "The order has not been dispatched yet."},
                    status=status.HTTP_409_CONFLICT,
                )

            if order.shipment_status != new_status:
                previous = order.shipment_status or "-"
                now = timezone.now()

                order.shipment_status = new_status
                order.shipment_status_updated_at = now
                if new_status == "Delivered":
                    if order.received_at is None:
                        order.received_at = now
                else:
                    order.received_at = None
                order.save()

                OrderLog.objects.create(
                    order=order,
                    title="Shipment Updated",
                    text=f"Shipment status changed from {previous} to {new_status}.",
                    created_by=user,
                )

                if new_status == "Delivered":
                    transaction.on_commit(
                        lambda: notify_gallery_managers(
                            "ORDER_DELIVERED",
                            title="Order delivered",
                            text=f"Order {order.order_number} has been delivered.",
                            sale=order.sale,
                            order=order,
                            actor=user,
                        )
                    )

        order = Order.objects.select_related(
            "sale__inquiry__customer", "sale__inquiry__rm"
        ).get(pk=pk)
        return Response(ShipmentRowSerializer(order).data)


def with_certificate_date(queryset):
    """Annotate each order with the date the certificate rules call for."""
    return queryset.annotate(
        cert_date=Case(
            When(
                sale__certificate_plan=SEPARATE_CERTIFICATE_PLAN,
                then=F("certificate_sent_at"),
            ),
            default=F("actual_dispatch_date"),
            output_field=DateTimeField(),
        )
    )


class GalleryCertificateListView(APIView):
    """
    GET /api/v1/gallery/certificates/
    Params: from, to, customerId, q, page, pageSize
    One row per order. Permission: certificates.view
    """

    permission_classes = [IsAuthenticated]

    def filtered_certificates(self, request):
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

        if errors:
            return None, Response(errors, status=status.HTTP_400_BAD_REQUEST)

        queryset = with_certificate_date(scope_orders(Order.objects.all(), user))

        if date_from:
            queryset = queryset.filter(cert_date__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(cert_date__date__lte=date_to)

        if customer_id:
            queryset = queryset.filter(sale__inquiry__customer_id=customer_id)

        q = (params.get("q") or "").strip()
        if q:
            queryset = queryset.filter(
                Q(order_number__icontains=q)
                | Q(sale__code__icontains=q)
                | Q(sale__inquiry__customer__name__icontains=q)
            )

        queryset = queryset.select_related(
            "sale__inquiry__customer", "sale__inquiry__rm"
        ).order_by(F("cert_date").desc(nulls_last=True), "-created_at", "-id")
        return queryset, None

    def get(self, request):
        require_permission(request.user, "certificates", "view")

        queryset, error = self.filtered_certificates(request)
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
                "results": CertificateRowSerializer(items, many=True).data,
            }
        )


class GalleryCertificateExportView(GalleryCertificateListView):
    """
    GET /api/v1/gallery/certificates/export/
    Same filters as the list (page and pageSize are ignored); returns every match.
    Permission: certificates.view
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        require_permission(request.user, "certificates", "view")

        queryset, error = self.filtered_certificates(request)
        if error:
            return error

        orders = list(queryset)
        rows = CertificateRowSerializer(orders, many=True).data

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="certificates-{timezone.localdate():%Y%m%d}.csv"'
        )
        response.write("\ufeff")  # BOM so Excel reads UTF-8 correctly

        writer = csv.writer(response)
        writer.writerow(
            [
                "Order Number",
                "Sale Number",
                "Customer",
                "Dispatch Date",
                "Sent Separately",
                "Certificate Dispatched",
            ]
        )
        for order, row in zip(orders, rows):
            if row["sentSeparately"]:
                certificate_dispatched = row["sentAt"] is not None
            else:
                certificate_dispatched = row["dispatched"]

            writer.writerow(
                [
                    _csv_safe(row["orderNumber"]),
                    _csv_safe(row["saleNumber"]),
                    _csv_safe(row["customerName"]),
                    (
                        timezone.localtime(order.cert_date).strftime("%Y-%m-%d")
                        if order.cert_date
                        else ""
                    ),
                    "Yes" if row["sentSeparately"] else "No",
                    "Yes" if certificate_dispatched else "No",
                ]
            )
        return response


class GallerySaleDetailView(APIView):
    """
    GET /api/v1/gallery/sales/{id}/
    Permission: sales.view (an RM only for their own sales)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        require_permission(user, "sales", "view")

        sale = get_object_or_404(
            Sale.objects.select_related(
                "inquiry__customer", "inquiry__rm", "email_status"
            ).prefetch_related(
                "products__artist",
                "products__order_product__order",
                "orders__order_products__sale_product",
                "orders__sale__inquiry__customer",
                "orders__sale__inquiry__rm",
            ),
            pk=pk,
        )

        # 403 (not 404) for an RM who doesn't own the sale.
        if user.role_id == RM_ROLE_ID and sale.inquiry.rm_id != user.id:
            raise PermissionDenied("You do not have permission to do this.")

        return Response(SaleDetailSerializer(sale).data)
