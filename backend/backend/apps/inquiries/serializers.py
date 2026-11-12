from rest_framework import serializers

from accounts.models import User
from .models import (
    Artist,
    Category,
    Customer,
    Inquiry,
    Subcategory,
    InquiryActivity
)
from decimal import Decimal
from django.db.models import Q, Sum


class InquiryListSerializer(serializers.ModelSerializer):

    customer = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    subcategory = serializers.SerializerMethodField()
    artist = serializers.SerializerMethodField()
    rm = serializers.SerializerMethodField()

    inquiryType = serializers.CharField(
        source="inquiry_type",
        read_only=True,
    )
    assignedOn = serializers.DateTimeField(
        source="assigned_on",
        read_only=True,
    )
    nextFollowUp = serializers.DateTimeField(
        source="next_follow_up",
        read_only=True,
    )
    nextAction = serializers.CharField(
        source="next_action",
        read_only=True,
        allow_null=True,
    )
    lastContact = serializers.DateTimeField(
        source="last_contact",
        read_only=True,
    )
    closedAt = serializers.DateTimeField(
        source="closed_at",
        read_only=True,
    )
    expectedTimeline = serializers.CharField(
        source="expected_timeline",
        read_only=True,
        allow_null=True,
    )
    budgetRange = serializers.CharField(
        source="budget_range",
        read_only=True,
        allow_null=True,
    )
    artStyle = serializers.CharField(
        source="art_style",
        read_only=True,
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(
        source="created_at",
        read_only=True,
    )
    updatedAt = serializers.DateTimeField(
        source="updated_at",
        read_only=True,
    )

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "code",
            "customer",
            "inquiryType",
            "requirement",
            "quantity",
            "value",
            "category",
            "subcategory",
            "artist",
            "source",
            "priority",
            "status",
            "rm",
            "assignedOn",
            "nextFollowUp",
            "nextAction",
            "lastContact",
            "closedAt",
            "notes",
            "expectedTimeline",
            "budgetRange",
            "artStyle",
            "createdAt",
            "updatedAt",
        ]

    def get_customer(self, obj):
        customer = obj.customer
        return {
            "id": str(customer.id),
            "code": customer.code,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "location": customer.location,
            "state": customer.state,
        }

    def get_category(self, obj):
        return {
            "id": str(obj.category.id),
            "name": obj.category.name,
        }

    def get_subcategory(self, obj):
        return {
            "id": str(obj.subcategory.id),
            "name": obj.subcategory.name,
        }

    def get_artist(self, obj):
        if not obj.artist:
            return None

        return {
            "id": str(obj.artist.id),
            "name": obj.artist.name,
        }

    def get_rm(self, obj):
        if not obj.rm:
            return None

        return {
            "id": str(obj.rm.id),
            "name": obj.rm.name,
        }


class InquiryCreateSerializer(serializers.Serializer):
    customerId = serializers.UUIDField()
    inquiryType = serializers.ChoiceField(
        choices=Inquiry.InquiryType.choices
    )
    source = serializers.ChoiceField(
        choices=Inquiry.Source.choices
    )
    requirement = serializers.CharField(max_length=500)
    quantity = serializers.IntegerField(min_value=1)
    value = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    categoryId = serializers.UUIDField()
    subcategoryId = serializers.UUIDField()
    artistId = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    rmId = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    priority = serializers.ChoiceField(
        choices=Inquiry.Priority.choices,
        required=False,
    )
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
    )
    expectedTimeline = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    budgetRange = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    artStyle = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_customerId(self, value):
        if not Customer.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Customer does not exist."
            )
        return value

    def validate_categoryId(self, value):
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Category does not exist."
            )
        return value

    def validate_subcategoryId(self, value):
        if not Subcategory.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Subcategory does not exist."
            )
        return value

    def validate_artistId(self, value):
        if value and not Artist.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Artist does not exist."
            )
        return value

    def validate_rmId(self, value):
        if value and not User.objects.filter(
            id=value,
            is_active=True,
            role_id="RM",
        ).exists():
            raise serializers.ValidationError(
                "Active RM does not exist."
            )
        return value

    def validate(self, attrs):
        category_id = attrs["categoryId"]
        subcategory_id = attrs["subcategoryId"]

        if not Subcategory.objects.filter(
            id=subcategory_id,
            category_id=category_id,
        ).exists():
            raise serializers.ValidationError({
                "subcategoryId": [
                    "Subcategory does not belong to the selected category."
                ]
            })

        return attrs


class InquiryActivitySerializer(serializers.ModelSerializer):
    createdBy = serializers.SerializerMethodField()

    class Meta:
        model = InquiryActivity
        fields = [
            "id",
            "action",
            "description",
            "metadata",
            "createdBy",
            "created_at",
        ]

    def get_createdBy(self, obj):
        if not obj.created_by:
            return None

        user = obj.created_by

        return {
            "id": str(user.id),
            "name": f"{user.email}".strip(),
        }


class CustomerListSerializer(serializers.ModelSerializer):
    altPhone = serializers.CharField(
        source="alt_phone",
        read_only=True,
        allow_null=True,
    )
    address1 = serializers.CharField(read_only=True)
    address2 = serializers.CharField(read_only=True)

    customerType = serializers.CharField(
        source="customer_type",
        read_only=True,
    )
    customerSince = serializers.DateTimeField(
        source="customer_since",
        read_only=True,
        allow_null=True,
    )
    createdAt = serializers.DateTimeField(
        source="created_at",
        read_only=True,
    )

    totalInquiries = serializers.SerializerMethodField()
    openInquiries = serializers.SerializerMethodField()
    wonInquiries = serializers.SerializerMethodField()
    totalValue = serializers.SerializerMethodField()
    lastActivityAt = serializers.SerializerMethodField()

    rm = serializers.SerializerMethodField()
    originalInquiry = serializers.SerializerMethodField()

    class Meta:
        model = Customer

        fields = [
            "id",
            "code",
            "name",
            "phone",
            "email",
            "location",
            "state",
            "altPhone",
            "address1",
            "address2",
            "pin",
            "country",
            "customerType",
            "customerSince",
            "status",
            "source",
            "originalInquiry",
            "rm",
            "notes",
            "createdAt",
            "totalInquiries",
            "openInquiries",
            "wonInquiries",
            "totalValue",
            "lastActivityAt",
        ]

    def get_rm(self, obj):
        if not obj.rm:
            return None

        return {
            "id": obj.rm.id,
            "name": obj.rm.name,
        }

    def get_originalInquiry(self, obj):
        inquiry = obj.inquiries.order_by("created_at").first()

        if not inquiry:
            return None

        return {
            "id": inquiry.id,
            "code": inquiry.code,
        }

    def get_totalInquiries(self, obj):
        return obj.inquiries.count()

    def get_openInquiries(self, obj):
        return obj.inquiries.exclude(
            status__in=[
                Inquiry.Status.WON,
                Inquiry.Status.LOST,
            ]
        ).count()

    def get_wonInquiries(self, obj):
        return obj.inquiries.filter(
            status=Inquiry.Status.WON
        ).count()

    def get_totalValue(self, obj):
        total = obj.inquiries.aggregate(
            total=Sum("value")
        )["total"]

        return total or 0

    def get_lastActivityAt(self, obj):
        last_inquiry = obj.inquiries.order_by(
            "-updated_at"
        ).first()

        if not last_inquiry:
            return None

        return last_inquiry.updated_at


class CustomerCreateSerializer(serializers.ModelSerializer):
    customerType = serializers.CharField(
        source="customer_type",
        required=False,
        default="Prospect",
    )

    class Meta:
        model = Customer
        fields = [
            "name",
            "phone",
            "email",
            "location",
            "state",
            "customerType",
            "notes",
        ]

    def validate(self, attrs):
        errors = {}

        phone = attrs.get("phone")
        email = attrs.get("email")

        if phone and Customer.objects.filter(phone=phone).exists():
            errors["phone"] = [
                "A customer with this phone number already exists."
            ]

        if email and Customer.objects.filter(
            email__iexact=email
        ).exists():
            errors["email"] = [
                "A customer with this email already exists."
            ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        last_customer = (
            Customer.objects
            .filter(code__startswith="CUST-")
            .order_by("-code")
            .first()
        )

        next_number = 1

        if last_customer:
            try:
                next_number = int(
                    last_customer.code.split("-")[-1]
                ) + 1
            except (ValueError, IndexError):
                pass

        code = f"CUST-{next_number:04d}"

        return Customer.objects.create(
            code=code,
            status="Active",
            source="Direct",
            **validated_data,
        )

class CustomerUpdateSerializer(serializers.ModelSerializer):
    customerType = serializers.CharField(
        source="customer_type",
        required=False,
    )

    altPhone = serializers.CharField(
        source="alt_phone",
        required=False,
        allow_null=True,
        allow_blank=True,
    )

    class Meta:
        model = Customer
        fields = [
            "name",
            "phone",
            "email",
            "location",
            "state",
            "altPhone",
            "address1",
            "address2",
            "pin",
            "country",
            "customerType",
            "status",
            "source",
            "notes",
        ]

    def validate_email(self, value):
        if not value:
            return value

        exists = (
            Customer.objects
            .filter(email__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if exists:
            raise serializers.ValidationError(
                "A customer with this email already exists."
            )

        return value

    def validate_phone(self, value):
        if not value:
            return value

        exists = (
            Customer.objects
            .filter(phone=value)
            .exclude(pk=self.instance.pk)
            .exists()
        )

        if exists:
            raise serializers.ValidationError(
                "A customer with this phone number already exists."
            )

        return value


class CustomerActivitySerializer(serializers.ModelSerializer):
    inquiryId = serializers.UUIDField(
        source="inquiry_id",
        read_only=True,
    )

    kind = serializers.CharField(
        source="action",
        read_only=True,
    )

    text = serializers.CharField(
        source="description",
        read_only=True,
    )

    method = serializers.SerializerMethodField()
    nextFollowUp = serializers.SerializerMethodField()
    by = serializers.SerializerMethodField()

    at = serializers.DateTimeField(
        source="created_at",
        read_only=True,
    )

    class Meta:
        model = InquiryActivity
        fields = [
            "id",
            "inquiryId",
            "kind",
            "method",
            "text",
            "nextFollowUp",
            "by",
            "at",
        ]

    def get_method(self, obj):
        return obj.metadata.get("method")

    def get_nextFollowUp(self, obj):
        return obj.metadata.get("nextFollowUp")

    def get_by(self, obj):
        if not obj.created_by:
            return None

        return {
            "id": obj.created_by.id,
            "name": obj.created_by.name,
        }


class MasterOptionSerializer(serializers.ModelSerializer):
    categoryId = serializers.SerializerMethodField()

    class Meta:
        model = Category  # We will dynamically use this serializer
        fields = [
            "id",
            "name",
            "categoryId",
        ]

    def get_categoryId(self, obj):
        if hasattr(obj, "category_id"):
            return obj.category_id
        return None