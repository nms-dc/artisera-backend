
import uuid

from django.conf import settings
from django.db import models


class Customer(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    code = models.CharField(
    max_length=30,
    unique=True,
    null=True,
    blank=True
)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    alt_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    address1 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    address2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    pin = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        default="India",
    )

    customer_type = models.CharField(
        max_length=50,
        default="Customer",
    )

    customer_since = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        default="Active",
    )

    source = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    rm = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Category(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="subcategories"
    )
    name = models.CharField(max_length=150)
    description = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name"],
                name="unique_subcategory_per_category"
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Artist(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="artists",
        null=True,
        blank=True,
    )

    nationality = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Inquiry(models.Model):

    class Source(models.TextChoices):
        WEBSITE = "Website", "Website"
        EMAIL = "Email", "Email"
        WHATSAPP = "WhatsApp", "WhatsApp"
        PHONE_WALKIN = "Phone / Walk-in", "Phone / Walk-in"
        INSTAGRAM = "Instagram", "Instagram"
        REFERRAL = "Referral", "Referral"
        EXHIBITION = "Exhibition", "Exhibition"
        OTHER = "Other", "Other"

    class InquiryType(models.TextChoices):
        PRODUCT = "Product Enquiry", "Product Enquiry"
        CUSTOM = "Custom Request", "Custom Request"
        PROJECT = "Project Enquiry", "Project Enquiry"
        GENERAL = "General / Other", "General / Other"

    class Status(models.TextChoices):
        TOUCHBASE = "Touchbase", "Touchbase"
        TOUCHBASE_FOLLOWUP = (
            "Touchbase Follow-up",
            "Touchbase Follow-up"
        )
        ACTIVE_CONVERSATIONS = (
            "Active Conversations",
            "Active Conversations"
        )
        NURTURE = "Nurture", "Nurture"
        WON = "Won", "Won"
        LOST = "Lost", "Lost"

    class Priority(models.TextChoices):
        LOW = "Low", "Low"
        MEDIUM = "Medium", "Medium"
        HIGH = "High", "High"
        URGENT = "Urgent", "Urgent"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    code = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )   

    # Customer relationship
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="inquiries"
    )

    # Inquiry classification
    inquiry_type = models.CharField(
        max_length=50,
        choices=InquiryType.choices,
        blank=True,
        default=""
    )

    requirement = models.CharField(
        max_length=500,
        blank=True,
        default=""
    )

    quantity = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="inquiries",
        null=True,
        blank=True
    )

    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="inquiries",
        null=True,
        blank=True
    )

    artist = models.ForeignKey(
        Artist,
        on_delete=models.SET_NULL,
        related_name="inquiries",
        null=True,
        blank=True
    )

    # Source and pipeline
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.OTHER
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.TOUCHBASE
    )

    # Relationship Manager assignment
    rm = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_inquiries",
        null=True,
        blank=True
    )

    assigned_on = models.DateTimeField(
        null=True,
        blank=True
    )

    # Follow-up tracking
    next_follow_up = models.DateTimeField(
        null=True,
        blank=True
    )

    next_action = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    last_contact = models.DateTimeField(
        null=True,
        blank=True
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Additional information
    notes = models.CharField(
        max_length=1000,
        blank=True,
        default=""
    )

    expected_timeline = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    budget_range = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    art_style = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code or 'New Inquiry'} - {self.customer.name}"



class InquiryActivity(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    action = models.CharField(max_length=50)

    description = models.CharField(max_length=500)

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiry_activities"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.inquiry.code} - {self.action}"
