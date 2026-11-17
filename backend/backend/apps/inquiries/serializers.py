from rest_framework import serializers

from accounts.models import User, RM_ROLE_ID
from .models import Artist, Category, Customer, Inquiry, Subcategory, InquiryActivity
from decimal import Decimal
from django.db.models import Q, Sum


class InquiryListSerializer(serializers.ModelSerializer):

    customer = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    subcategory = serializers.SerializerMethodField()
    artist = serializers.SerializerMethodField()
    rm = serializers.SerializerMethodField()
    repeatProspect = serializers.SerializerMethodField()
    sale = serializers.SerializerMethodField()

    value = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        coerce_to_string=False,
        read_only=True,
    )

    inquiryType = serializers.CharField(source="inquiry_type", read_only=True)
    assignedOn = serializers.DateTimeField(
        source="assigned_on", read_only=True, allow_null=True
    )
    nextFollowUp = serializers.DateTimeField(
        source="next_follow_up", read_only=True, allow_null=True
    )
    nextAction = serializers.CharField(
        source="next_action", read_only=True, allow_null=True
    )
    lastContact = serializers.DateTimeField(
        source="last_contact", read_only=True, allow_null=True
    )
    closedAt = serializers.DateTimeField(
        source="closed_at", read_only=True, allow_null=True
    )
    expectedTimeline = serializers.CharField(
        source="expected_timeline", read_only=True, allow_null=True
    )
    budgetRange = serializers.CharField(
        source="budget_range", read_only=True, allow_null=True
    )
    artStyle = serializers.CharField(
        source="art_style", read_only=True, allow_null=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

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
            "repeatProspect",
            "sale",
            "createdAt",
            "updatedAt",
        ]

    @staticmethod
    def _ref(obj):
        return {"id": str(obj.id), "name": obj.name} if obj else None

    def get_customer(self, obj):
        c = obj.customer
        if not c:
            return None
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

    def get_category(self, obj):
        return self._ref(obj.category)

    def get_subcategory(self, obj):
        return self._ref(obj.subcategory)

    def get_artist(self, obj):
        return self._ref(obj.artist)

    def get_rm(self, obj):
        return self._ref(obj.rm)

    def get_repeatProspect(self, obj):
        # Prefer the annotation set in the view (no extra query per row)
        annotated = getattr(obj, "repeat_prospect", None)
        if annotated is not None:
            return annotated
        return (
            Inquiry.objects.filter(customer_id=obj.customer_id)
            .exclude(pk=obj.pk)
            .exists()
        )

    def get_sale(self, obj):
        return None  # until a Sale model exists


class InquiryCreateSerializer(serializers.Serializer):
    customerId = serializers.UUIDField()
    inquiryType = serializers.ChoiceField(choices=Inquiry.InquiryType.choices)
    source = serializers.ChoiceField(choices=Inquiry.Source.choices)
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
            raise serializers.ValidationError("Customer does not exist.")
        return value

    def validate_categoryId(self, value):
        if not Category.objects.filter(id=value).exists():
            raise serializers.ValidationError("Category does not exist.")
        return value

    def validate_subcategoryId(self, value):
        if not Subcategory.objects.filter(id=value).exists():
            raise serializers.ValidationError("Subcategory does not exist.")
        return value

    def validate_artistId(self, value):
        if value and not Artist.objects.filter(id=value).exists():
            raise serializers.ValidationError("Artist does not exist.")
        return value

    def validate_rmId(self, value):
        if (
            value
            and not User.objects.filter(
                id=value,
                is_active=True,
                role_id="RM",
            ).exists()
        ):
            raise serializers.ValidationError("Active RM does not exist.")
        return value

    def validate(self, attrs):
        category_id = attrs.get("categoryId")
        subcategory_id = attrs.get("subcategoryId")

        # On PATCH, fall back to the existing inquiry's values
        instance = self.context.get("instance")
        if instance is not None:
            category_id = category_id or instance.category_id
            subcategory_id = subcategory_id or instance.subcategory_id

        if category_id and subcategory_id:
            if not Subcategory.objects.filter(
                id=subcategory_id, category_id=category_id
            ).exists():
                raise serializers.ValidationError(
                    {
                        "subcategoryId": [
                            "Subcategory does not belong to the selected category."
                        ]
                    }
                )
        return attrs


class InquiryActivitySerializer(serializers.ModelSerializer):
    inquiryId = serializers.SerializerMethodField()
    kind = serializers.CharField(source="action", read_only=True)
    method = serializers.SerializerMethodField()
    text = serializers.CharField(source="description", read_only=True)
    nextFollowUp = serializers.SerializerMethodField()
    by = serializers.SerializerMethodField()
    at = serializers.DateTimeField(source="created_at", read_only=True)

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

    def get_inquiryId(self, obj):
        return str(obj.inquiry_id)

    def get_method(self, obj):
        return (obj.metadata or {}).get("method")

    def get_nextFollowUp(self, obj):
        return (obj.metadata or {}).get("nextFollowUp")

    def get_by(self, obj):
        user = obj.created_by
        return {"id": str(user.id), "name": user.name} if user else None


class CustomerListSerializer(serializers.ModelSerializer):
    altPhone = serializers.SerializerMethodField()
    address2 = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    customerType = serializers.CharField(source="customer_type", read_only=True)
    customerSince = serializers.DateTimeField(
        source="customer_since", read_only=True, allow_null=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    repeatProspect = serializers.SerializerMethodField()
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
            "address1",
            "address2",
            "pin",
            "country",
            "altPhone",
            "customerType",
            "repeatProspect",
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

    # --- nullable text fields: "" -> null, as in the FE sample ---
    def get_altPhone(self, obj):
        return obj.alt_phone or None

    def get_address2(self, obj):
        return obj.address2 or None

    def get_notes(self, obj):
        return obj.notes or None

    def get_rm(self, obj):
        if not obj.rm:
            return None
        return {"id": str(obj.rm.id), "name": obj.rm.name}

    # --- counters: use annotations from the view, fall back to queries ---
    def _annotated(self, obj, attr, fallback):
        value = getattr(obj, attr, None)
        return value if value is not None else fallback()

    def get_totalInquiries(self, obj):
        return self._annotated(obj, "total_inquiries", lambda: obj.inquiries.count())

    def get_openInquiries(self, obj):
        return self._annotated(
            obj,
            "open_inquiries",
            lambda: obj.inquiries.exclude(
                status__in=[Inquiry.Status.WON, Inquiry.Status.LOST]
            ).count(),
        )

    def get_wonInquiries(self, obj):
        return self._annotated(
            obj,
            "won_inquiries",
            lambda: obj.inquiries.filter(status=Inquiry.Status.WON).count(),
        )

    def get_totalValue(self, obj):
        total = getattr(obj, "total_value", None)
        if total is None:
            total = obj.inquiries.aggregate(t=Sum("value"))["t"]
        return float(total or 0)

    def get_lastActivityAt(self, obj):
        value = getattr(obj, "last_activity_at", None)
        if value is None:
            last = obj.inquiries.order_by("-updated_at").first()
            value = last.updated_at if last else None
        return value

    def get_repeatProspect(self, obj):
        return self.get_totalInquiries(obj) > 1

    def get_originalInquiry(self, obj):
        first = getattr(obj, "first_inquiry", None)  # prefetched list, see view
        if first is not None:
            inquiry = first[0] if first else None
        else:
            inquiry = obj.inquiries.order_by("created_at").first()
        if not inquiry:
            return None
        return {"id": str(inquiry.id), "code": inquiry.code}


class CustomerCreateSerializer(serializers.ModelSerializer):
    customerType = serializers.CharField(
        source="customer_type", required=False, default="Prospect"
    )
    rmId = serializers.UUIDField(required=False, allow_null=True)
    state = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

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
            "rmId",
        ]

    def validate_phone(self, value):
        value = (value or "").strip()
        if value and Customer.objects.filter(phone=value).exists():
            raise serializers.ValidationError(
                "A customer with this phone number already exists."
            )
        return value

    def validate_email(self, value):
        value = (value or "").strip().lower()
        if value and Customer.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A customer with this email already exists."
            )
        return value

    def validate_rmId(self, value):
        if (
            value
            and not User.objects.filter(
                id=value, is_active=True, role_id=RM_ROLE_ID
            ).exists()
        ):
            raise serializers.ValidationError("Active RM does not exist.")
        return value

    def create(self, validated_data):
        rm_id = validated_data.pop("rmId", None)

        last_customer = (
            Customer.objects.filter(code__startswith="CUST-").order_by("-code").first()
        )
        next_number = 1
        if last_customer:
            try:
                next_number = int(last_customer.code.split("-")[-1]) + 1
            except (ValueError, IndexError):
                pass

        return Customer.objects.create(
            code=f"CUST-{next_number:04d}",
            status="Active",
            source="Direct",
            rm_id=rm_id,
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
            Customer.objects.filter(email__iexact=value)
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
            Customer.objects.filter(phone=value).exclude(pk=self.instance.pk).exists()
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
