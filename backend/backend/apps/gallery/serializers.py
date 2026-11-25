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
from decimal import Decimal
from django.utils import timezone
from .services import COURIERS, PACKAGING_TYPES
from .services import COURIERS, PACKAGING_TYPES, SHIPMENT_STATUSES
import os

# Starting lists; the spec only shows "Tube" and "DHL". Edit here to change them.
PACKAGING_TYPES = ["Tube", "Box", "Crate", "Envelope", "Pallet", "Other"]
COURIERS = ["DHL", "FedEx", "UPS", "Blue Dart", "DTDC", "India Post", "Other"]


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


# ========================= gallery sales orders =================
def _dt(value):
    return serializers.DateTimeField().to_representation(value) if value else None


def _num(value):
    return float(value) if value is not None else None


class OrderCreateSerializer(serializers.Serializer):
    groups = serializers.ListField(
        child=serializers.ListField(child=serializers.UUIDField(), allow_empty=False),
        allow_empty=False,
    )

    def validate_groups(self, value):
        seen = set()
        for group in value:
            for product_id in group:
                if product_id in seen:
                    raise serializers.ValidationError(
                        "A product can appear in only one group."
                    )
                seen.add(product_id)
        return value


class OrderDetailSerializer(OrderListSerializer):
    inquiry = serializers.SerializerMethodField()
    saleDate = serializers.DateTimeField(source="sale.sale_date", read_only=True)
    products = serializers.SerializerMethodField()
    readyForPacking = serializers.BooleanField(
        source="ready_for_packing", read_only=True
    )
    packages = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    courier = serializers.SerializerMethodField()
    waybill = serializers.SerializerMethodField()
    actualDispatchDate = serializers.DateTimeField(
        source="actual_dispatch_date", read_only=True, allow_null=True
    )
    certificateIncluded = serializers.BooleanField(
        source="certificate_included", read_only=True
    )
    invoiceIncluded = serializers.BooleanField(
        source="invoice_included", read_only=True
    )
    shipmentStatus = serializers.SerializerMethodField()
    receivedAt = serializers.DateTimeField(
        source="received_at", read_only=True, allow_null=True
    )
    certificateSentAt = serializers.DateTimeField(
        source="certificate_sent_at", read_only=True, allow_null=True
    )

    class Meta(OrderListSerializer.Meta):
        fields = OrderListSerializer.Meta.fields + [
            "inquiry",
            "saleDate",
            "products",
            "readyForPacking",
            "packages",
            "media",
            "courier",
            "waybill",
            "actualDispatchDate",
            "certificateIncluded",
            "invoiceIncluded",
            "shipmentStatus",
            "receivedAt",
            "certificateSentAt",
        ]

    def get_inquiry(self, obj):
        inquiry = obj.sale.inquiry
        return {"id": str(inquiry.id), "code": inquiry.code}

    def get_products(self, obj):
        items = []
        for order_product in obj.order_products.all():
            data = dict(SaleProductSerializer(order_product.sale_product).data)
            data["photoVideoUploaded"] = order_product.photo_video_uploaded
            items.append(data)
        return items

    def get_packages(self, obj):
        return [
            {
                "id": str(p.id),
                "packagingType": p.packaging_type,
                "lengthCm": _num(p.length_cm),
                "widthCm": _num(p.width_cm),
                "heightCm": _num(p.height_cm),
                "weightKg": _num(p.weight_kg),
                "notes": p.notes,
            }
            for p in obj.packages.all()
        ]

    def get_media(self, obj):
        request = self.context.get("request")
        items = []
        for m in obj.media.all():
            url = m.file.url
            if request:
                url = request.build_absolute_uri(url)
            items.append(
                {
                    "id": str(m.id),
                    "kind": m.kind,
                    "type": m.type,
                    "fileName": m.file_name,
                    "url": url,
                    "size": m.size,
                    "uploadedAt": _dt(m.uploaded_at),
                }
            )
        return items

    def get_courier(self, obj):
        return obj.courier or None

    def get_waybill(self, obj):
        return obj.waybill or None

    def get_shipmentStatus(self, obj):
        return obj.shipment_status or None


class OrderSaveProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    photoVideoUploaded = serializers.BooleanField()


class OrderSaveSerializer(serializers.Serializer):
    readyForPacking = serializers.BooleanField(required=False)
    products = OrderSaveProductSerializer(many=True, required=False)

    def validate_products(self, value):
        ids = [item["id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("A product can appear only once.")
        return value


class LogEntrySerializer(serializers.Serializer):
    """Shared shape for order and sale log entries."""

    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    text = serializers.CharField(read_only=True)
    by = serializers.SerializerMethodField()
    at = serializers.DateTimeField(source="created_at", read_only=True)

    def get_by(self, obj):
        return _ref(obj.created_by)


ALLOWED_MEDIA_TYPES = {
    "image/jpeg": ("image", (".jpg", ".jpeg")),
    "image/png": ("image", (".png",)),
    "video/mp4": ("video", (".mp4",)),
}
MAX_MEDIA_BYTES = 100 * 1024 * 1024  # 100 MB


class OrderMediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    kind = serializers.ChoiceField(
        choices=["product", "packing"], required=False, default="product"
    )

    def validate_file(self, f):
        content_type = (getattr(f, "content_type", "") or "").lower()
        if content_type not in ALLOWED_MEDIA_TYPES:
            raise serializers.ValidationError(
                "Only image/jpeg, image/png and video/mp4 files are allowed."
            )
        _, extensions = ALLOWED_MEDIA_TYPES[content_type]
        if os.path.splitext(f.name)[1].lower() not in extensions:
            raise serializers.ValidationError(
                "The file extension does not match its type."
            )
        if f.size > MAX_MEDIA_BYTES:
            raise serializers.ValidationError("The file must be 100 MB or smaller.")
        return f


def serialize_media(media, request=None):
    url = media.file.url
    if request is not None:
        url = request.build_absolute_uri(url)
    return {
        "id": str(media.id),
        "kind": media.kind,
        "type": media.type,
        "fileName": media.file_name,
        "url": url,
        "size": media.size,
        "uploadedAt": _dt(media.uploaded_at),
    }


class PackageInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    packagingType = serializers.ChoiceField(choices=PACKAGING_TYPES)
    lengthCm = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    widthCm = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    heightCm = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    weightKg = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        for field in ("lengthCm", "widthCm", "heightCm", "weightKg"):
            value = attrs.get(field)
            if value is not None and value <= Decimal("0"):
                raise serializers.ValidationError({field: ["Must be greater than 0."]})
        return attrs


class OrderDispatchSerializer(serializers.Serializer):
    packages = PackageInputSerializer(many=True, required=False, allow_empty=False)
    courier = serializers.ChoiceField(choices=COURIERS, required=False)
    waybill = serializers.CharField(max_length=100, required=False, allow_blank=True)
    actualDispatchDate = serializers.DateField(required=False, allow_null=True)
    certificateIncluded = serializers.BooleanField(required=False)
    invoiceIncluded = serializers.BooleanField(required=False)

    def validate_actualDispatchDate(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError(
                "The dispatch date cannot be in the future."
            )
        return value


class OrderReceivedSerializer(serializers.Serializer):
    received = serializers.BooleanField()
    date = serializers.DateField(required=False, allow_null=True)

    def validate_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("The date cannot be in the future.")
        return value


class OrderCertificateSentSerializer(serializers.Serializer):
    sent = serializers.BooleanField()
    date = serializers.DateField(required=False, allow_null=True)

    def validate_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("The date cannot be in the future.")
        return value


class ShipmentRowSerializer(serializers.ModelSerializer):
    orderId = serializers.UUIDField(source="id", read_only=True)
    orderNumber = serializers.CharField(source="order_number", read_only=True)
    saleId = serializers.UUIDField(source="sale_id", read_only=True)
    saleNumber = serializers.CharField(source="sale.code", read_only=True)
    customerName = serializers.CharField(
        source="sale.inquiry.customer.name", read_only=True
    )
    rmName = serializers.SerializerMethodField()
    courier = serializers.SerializerMethodField()
    trackingNo = serializers.SerializerMethodField()
    dispatchDate = serializers.DateTimeField(
        source="actual_dispatch_date", read_only=True
    )
    status = serializers.SerializerMethodField()
    statusUpdatedAt = serializers.DateTimeField(
        source="shipment_status_updated_at", read_only=True, allow_null=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "orderId",
            "orderNumber",
            "saleId",
            "saleNumber",
            "customerName",
            "rmName",
            "courier",
            "trackingNo",
            "dispatchDate",
            "status",
            "statusUpdatedAt",
        ]

    def get_rmName(self, obj):
        rm = obj.sale.inquiry.rm
        return rm.name if rm else None

    def get_courier(self, obj):
        return obj.courier or None

    def get_trackingNo(self, obj):
        return obj.waybill or None

    def get_status(self, obj):
        return obj.shipment_status or None


class ShipmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SHIPMENT_STATUSES)


class CertificateRowSerializer(serializers.ModelSerializer):
    orderId = serializers.UUIDField(source="id", read_only=True)
    orderNumber = serializers.CharField(source="order_number", read_only=True)
    saleId = serializers.UUIDField(source="sale_id", read_only=True)
    saleNumber = serializers.CharField(source="sale.code", read_only=True)
    customerName = serializers.CharField(
        source="sale.inquiry.customer.name", read_only=True
    )
    rmName = serializers.SerializerMethodField()
    dispatchDate = serializers.DateTimeField(
        source="cert_date", read_only=True, allow_null=True
    )
    sentSeparately = serializers.SerializerMethodField()
    dispatched = serializers.SerializerMethodField()
    sentAt = serializers.DateTimeField(
        source="certificate_sent_at", read_only=True, allow_null=True
    )

    class Meta:
        model = Order
        fields = [
            "id",
            "orderId",
            "orderNumber",
            "saleId",
            "saleNumber",
            "customerName",
            "rmName",
            "dispatchDate",
            "sentSeparately",
            "dispatched",
            "sentAt",
        ]

    def get_rmName(self, obj):
        rm = obj.sale.inquiry.rm
        return rm.name if rm else None

    def get_sentSeparately(self, obj):
        return obj.sale.certificate_plan == SEPARATE_CERTIFICATE_PLAN

    def get_dispatched(self, obj):
        return obj.actual_dispatch_date is not None


class SaleDetailSerializer(SaleListSerializer):
    rmNotification = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()
    shipmentPriority = serializers.CharField(source="shipment_priority", read_only=True)
    requiredShipmentDate = serializers.DateTimeField(
        source="required_shipment_date", read_only=True, allow_null=True
    )
    shipmentInstructions = serializers.SerializerMethodField()
    paymentNotes = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    orders = serializers.SerializerMethodField()

    class Meta(SaleListSerializer.Meta):
        fields = SaleListSerializer.Meta.fields + [
            "rmNotification",
            "notes",
            "shipmentPriority",
            "requiredShipmentDate",
            "shipmentInstructions",
            "paymentNotes",
            "products",
            "orders",
        ]

    def _email(self, obj):
        try:
            return obj.email_status
        except ObjectDoesNotExist:
            return None

    def get_rmNotification(self, obj):
        email = self._email(obj)
        if email and email.received_at:
            email_status = "Received"
        elif email and email.rm_email_sent_at:
            email_status = "Sent"
        else:
            email_status = "Pending"
        return {
            "status": email_status,
            "at": _dt(email.received_at) if email else None,
            "sentAt": _dt(email.rm_email_sent_at) if email else None,
            "overridden": bool(email.overridden) if email else False,
        }

    def get_notes(self, obj):
        return obj.notes or None

    def get_shipmentInstructions(self, obj):
        return obj.shipment_instructions or None

    def get_paymentNotes(self, obj):
        return obj.payment_notes or None

    def get_products(self, obj):
        return SaleProductSerializer(obj.products.all(), many=True).data

    def get_orders(self, obj):
        orders = sorted(obj.orders.all(), key=lambda o: o.created_at, reverse=True)
        return OrderListSerializer(orders, many=True).data
