import uuid

from django.conf import settings
from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def gallery_storage():
    return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)


class SaleEmailStatus(models.Model):
    """RM email tracking for a sale (one row per sale, created on demand)."""

    sale = models.OneToOneField(
        "inquiries.Sale", on_delete=models.CASCADE, related_name="email_status"
    )
    rm_email_sent_at = models.DateTimeField(null=True, blank=True)  # RM marked "sent"
    received_at = models.DateTimeField(null=True, blank=True)  # gallery got it
    overridden = models.BooleanField(default=False)  # received via override
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email status for {self.sale.code}"


class SaleLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        "inquiries.Sale", on_delete=models.CASCADE, related_name="logs"
    )
    title = models.CharField(max_length=100)
    text = models.CharField(max_length=500, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(
        "inquiries.Sale", on_delete=models.PROTECT, related_name="orders"
    )
    # Equals the sale number when one order holds every product, otherwise
    # "<sale number>-A", "-B", ... in creation order.
    order_number = models.CharField(max_length=40, unique=True)

    certificate_included = models.BooleanField(default=True)
    invoice_included = models.BooleanField(default=True)

    ready_for_packing = models.BooleanField(default=False)

    # Shipment (filled by the dispatch call)
    courier = models.CharField(max_length=100, blank=True, default="")
    waybill = models.CharField(max_length=100, blank=True, default="")
    actual_dispatch_date = models.DateTimeField(null=True, blank=True)
    shipment_status = models.CharField(max_length=30, blank=True, default="")
    shipment_status_updated_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    certificate_sent_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)  # = "orderDate"
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number


class OrderProduct(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="order_products"
    )
    # OneToOne enforces "a product appears in only one order".
    sale_product = models.OneToOneField(
        "inquiries.SaleProduct",
        on_delete=models.PROTECT,
        related_name="order_product",
    )
    photo_video_uploaded = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]


class Package(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="packages")
    packaging_type = models.CharField(max_length=50)
    length_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    width_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    height_cm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    weight_kg = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    notes = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["id"]


class OrderMedia(models.Model):
    class Kind(models.TextChoices):
        PRODUCT = "product", "Product"
        PACKING = "packing", "Packing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="media")
    order_product = models.ForeignKey(
        OrderProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="media",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PRODUCT)
    type = models.CharField(max_length=10)  # "image" | "video"
    file = models.FileField(upload_to="gallery/orders/%Y/%m/", storage=gallery_storage)
    file_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]


class OrderLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="logs")
    title = models.CharField(max_length=100)
    text = models.CharField(max_length=500, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
