from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist
from .models import Order
from .services import (
    SEPARATE_CERTIFICATE_PLAN,
    derive_status,
    sale_email_confirmed,
    sale_pending_with,
)
from inquiries.models import Sale, SaleProduct
import datetime as dt


def _ref(user):
    return {"id": str(user.id), "name": user.name} if user else None


class OrderListSerializer(serializers.ModelSerializer):
    """Order row used by the dashboard and (later) the orders list."""

    orderNumber = serializers.CharField(source="order_number", read_only=True)
    saleId = serializers.UUIDField(source="sale_id", read_only=True)
    saleNumber = serializers.CharField(source="sale.code", read_only=True)
    customer = serializers.SerializerMethodField()
    rm = serializers.SerializerMethodField()
    orderDate = serializers.DateTimeField(source="created_at", read_only=True)
    totalProducts = serializers.SerializerMethodField()
    orderValue = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    certificateSeparately = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "orderNumber",
            "saleId",
            "saleNumber",
            "customer",
            "rm",
            "orderDate",
            "totalProducts",
            "orderValue",
            "status",
            "certificateSeparately",
        ]

    def get_customer(self, obj):
        return _ref(obj.sale.inquiry.customer)

    def get_rm(self, obj):
        return _ref(obj.sale.inquiry.rm)

    def get_totalProducts(self, obj):
        return sum(op.sale_product.quantity for op in obj.order_products.all())

    def get_orderValue(self, obj):
        return float(
            sum(
                op.sale_product.listed_price * op.sale_product.quantity
                for op in obj.order_products.all()
            )
        )

    def get_status(self, obj):
        return derive_status(obj)

    def get_certificateSeparately(self, obj):
        return obj.sale.certificate_plan == SEPARATE_CERTIFICATE_PLAN


class AttentionSaleSerializer(serializers.ModelSerializer):
    saleNumber = serializers.CharField(source="code", read_only=True)
    customerName = serializers.CharField(source="inquiry.customer.name", read_only=True)
    saleDate = serializers.DateTimeField(source="sale_date", read_only=True)
    totalValue = serializers.DecimalField(
        source="total_value",
        max_digits=14,
        decimal_places=2,
        coerce_to_string=False,
        read_only=True,
    )
    emailConfirmed = serializers.SerializerMethodField()
    pendingWith = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "saleNumber",
            "customerName",
            "saleDate",
            "totalValue",
            "emailConfirmed",
            "pendingWith",
        ]

    def get_emailConfirmed(self, obj):
        return sale_email_confirmed(obj)

    def get_pendingWith(self, obj):
        return sale_pending_with(obj)


class SaleListSerializer(serializers.ModelSerializer):
    saleNumber = serializers.CharField(source="code", read_only=True)
    inquiry = serializers.SerializerMethodField()
    customer = serializers.SerializerMethodField()
    rm = serializers.SerializerMethodField()
    emailConfirmed = serializers.SerializerMethodField()
    saleDate = serializers.DateTimeField(source="sale_date", read_only=True)
    totalValue = serializers.DecimalField(
        source="total_value",
        max_digits=14,
        decimal_places=2,
        coerce_to_string=False,
        read_only=True,
    )
    totalOrders = serializers.SerializerMethodField()
    totalProducts = serializers.SerializerMethodField()
    productsRemaining = serializers.SerializerMethodField()
    certificatePlan = serializers.CharField(source="certificate_plan", read_only=True)
    certificateSeparately = serializers.SerializerMethodField()
    paymentStatus = serializers.CharField(source="payment_status", read_only=True)
    pendingWith = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = [
            "id",
            "saleNumber",
            "inquiry",
            "customer",
            "rm",
            "emailConfirmed",
            "saleDate",
            "totalValue",
            "totalOrders",
            "totalProducts",
            "productsRemaining",
            "certificatePlan",
            "certificateSeparately",
            "paymentStatus",
            "pendingWith",
        ]

    def get_inquiry(self, obj):
        return {"id": str(obj.inquiry_id), "code": obj.inquiry.code}

    def get_customer(self, obj):
        c = obj.inquiry.customer
        return {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "location": c.location,
            "state": c.state,
            "address1": c.address1,
            "address2": c.address2 or None,
            "pin": c.pin,
            "country": c.country,
        }

    def get_rm(self, obj):
        return _ref(obj.inquiry.rm)

    def get_emailConfirmed(self, obj):
        return sale_email_confirmed(obj)

    def get_totalOrders(self, obj):
        return len(obj.orders.all())

    def get_totalProducts(self, obj):
        return sum(p.quantity for p in obj.products.all())

    def get_productsRemaining(self, obj):
        # Units of products that are not yet part of any order.
        ordered_ids = {
            op.sale_product_id
            for order in obj.orders.all()
            for op in order.order_products.all()
        }
        return sum(p.quantity for p in obj.products.all() if p.id not in ordered_ids)

    def get_certificateSeparately(self, obj):
        return obj.certificate_plan == SEPARATE_CERTIFICATE_PLAN

    def get_pendingWith(self, obj):
        return sale_pending_with(obj)


class SaleProductSerializer(serializers.ModelSerializer):
    artist = serializers.SerializerMethodField()
    imageUrl = serializers.SerializerMethodField()
    listedPrice = serializers.DecimalField(
        source="listed_price",
        max_digits=14,
        decimal_places=2,
        coerce_to_string=False,
        read_only=True,
    )
    productStatus = serializers.CharField(source="product_status", read_only=True)
    commissionReadyDate = serializers.SerializerMethodField()
    orderNotes = serializers.SerializerMethodField()
    orderId = serializers.SerializerMethodField()
    orderNumber = serializers.SerializerMethodField()

    class Meta:
        model = SaleProduct
        fields = [
            "id",
            "name",
            "artist",
            "url",
            "imageUrl",
            "listedPrice",
            "quantity",
            "productStatus",
            "commissionReadyDate",
            "orderNotes",
            "orderId",
            "orderNumber",
        ]

    def get_artist(self, obj):
        return _ref(obj.artist)

    def get_imageUrl(self, obj):
        return None  # no product image is stored yet

    def get_commissionReadyDate(self, obj):
        if not obj.commission_ready_date:
            return None
        return obj.commission_ready_date.astimezone(dt.timezone.utc).date().isoformat()

    def get_orderNotes(self, obj):
        return obj.order_notes or None

    def _order(self, obj):
        try:
            return obj.order_product.order
        except ObjectDoesNotExist:
            return None

    def get_orderId(self, obj):
        order = self._order(obj)
        return str(order.id) if order else None

    def get_orderNumber(self, obj):
        order = self._order(obj)
        return order.order_number if order else None


class SaleProductUpdateSerializer(serializers.Serializer):
    productStatus = serializers.CharField(max_length=50, required=False)
    commissionReadyDate = serializers.DateField(required=False, allow_null=True)
    orderNotes = serializers.CharField(
        max_length=300, required=False, allow_blank=True, allow_null=True
    )
