from datetime import timedelta
from django.utils import timezone
from datetime import timedelta, timezone as dt_timezone
from django.db.models import Exists, OuterRef, Q, Count, Sum, Max, Prefetch
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from .models import Inquiry, InquiryActivity
from .serializers import (
    InquiryListSerializer,
    InquiryCreateSerializer,
    InquiryActivitySerializer,
    InquiryBulkSerializer,
    InquiryStatusSerializer,
    InquiryTouchbaseSerializer,
    InquiryInteractionSerializer,
    InquirySnoozeSerializer,
)
from inquiries.models import Customer, Category, Subcategory, Artist
from inquiries.serializers import (
    CustomerListSerializer,
    CustomerCreateSerializer,
    CustomerUpdateSerializer,
    CustomerActivitySerializer,
    CustomerSaleSerializer,
)
from rest_framework import status
from django.db import transaction
from accounts.models import User, RM_ROLE_ID
from .serializers import InquiryAssignSerializer  # add to your existing import list
from .models import Inquiry, InquiryActivity, Sale, SaleProduct
from .serializers import InquiryWonSerializer

MAX_PAGE_SIZE = 100


def _parse_value_band(band):
    """
    Accepts "min-max" (e.g. "50000-200000") or "min+" (e.g. "500000+").
    Returns a Q filter, or None if the format isn't recognised.
    """
    band = band.strip()
    try:
        if band.endswith("+"):
            return Q(value__gte=float(band[:-1]))
        if "-" in band:
            low, high = band.split("-", 1)
            return Q(value__gte=float(low), value__lte=float(high))
    except ValueError:
        pass
    return None


class InquiryListView(APIView):

    def get_queryset(
        self, request, apply_tab=True, apply_status=True, with_repeat=True
    ):
        user = request.user
        params = request.query_params
        queryset = Inquiry.objects.select_related(
            "customer", "category", "subcategory", "artist", "rm"
        )

        # The repeat_prospect subquery is only needed for the list, not for counts
        if with_repeat:
            queryset = queryset.annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )

        # RM users only see their own inquiries
        if not user.is_admin:
            queryset = queryset.filter(rm=user)

        # ---- Tab ----
        tab_filters = {
            "unassigned": Q(rm__isnull=True),
            "assigned": Q(rm__isnull=False),
            "touchbase": Q(status=Inquiry.Status.TOUCHBASE),
            "followup": Q(status=Inquiry.Status.TOUCHBASE_FOLLOWUP),
            "active": Q(status=Inquiry.Status.ACTIVE_CONVERSATIONS),
            "nurture": Q(status=Inquiry.Status.NURTURE),
            "won": Q(status=Inquiry.Status.WON),
            "lost": Q(status=Inquiry.Status.LOST),
        }
        if apply_tab:
            tab = params.get("tab", "all")
            if tab == "today":
                queryset = queryset.filter(next_follow_up__date=timezone.localdate())
            elif tab in tab_filters:
                queryset = queryset.filter(tab_filters[tab])

        # ---- Search ----
        q = params.get("q")
        if q:
            queryset = queryset.filter(
                Q(customer__name__icontains=q)
                | Q(customer__email__icontains=q)
                | Q(customer__phone__icontains=q)
                | Q(code__icontains=q)
            )

        # ---- Simple filters ----
        if params.get("priority"):
            queryset = queryset.filter(priority=params["priority"])
        if params.get("source"):
            queryset = queryset.filter(source=params["source"])
        if params.get("customerId"):
            queryset = queryset.filter(customer_id=params["customerId"])
        if params.get("rmId") and user.is_admin:  # RMs are already scoped to themselves
            queryset = queryset.filter(rm_id=params["rmId"])

        # status: single value or comma-separated list
        if apply_status and params.get("status"):
            statuses = [s.strip() for s in params["status"].split(",") if s.strip()]
            queryset = queryset.filter(status__in=statuses)

        # valueBand
        if params.get("valueBand"):
            band_q = _parse_value_band(params["valueBand"])
            if band_q is not None:
                queryset = queryset.filter(band_q)

        # ---- dateRange: "today" or number of days ----
        date_range = params.get("dateRange")
        if date_range:
            if date_range == "today":
                queryset = queryset.filter(created_at__date=timezone.localdate())
            else:
                try:
                    days = int(date_range)
                    if days > 0:
                        queryset = queryset.filter(
                            created_at__gte=timezone.now() - timedelta(days=days)
                        )
                except ValueError:
                    pass

        # ---- Ordering ----
        ordering_map = {
            "createdAt": "created_at",
            "-createdAt": "-created_at",
            "nextFollowUp": "next_follow_up",
            "-nextFollowUp": "-next_follow_up",
            "value": "value",
            "-value": "-value",
        }
        ordering = ordering_map.get(params.get("ordering", "-createdAt"), "-created_at")
        return queryset.order_by(ordering, "-id")  # "-id" keeps pages stable on ties

    def get(self, request):
        queryset = self.get_queryset(request)

        def _int(name, default, minimum=1, maximum=None):
            try:
                value = int(request.query_params.get(name, default))
            except (TypeError, ValueError):
                return default
            value = max(value, minimum)
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
                "results": InquiryListSerializer(items, many=True).data,
            }
        )

    def post(self, request):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        can_assign_rm = user.is_admin or user.can("inquiries", "assignRm")

        if can_assign_rm:
            rm_id = data.get("rmId")
            priority = data.get("priority", Inquiry.Priority.NORMAL)
        else:
            rm_id = user.id
            priority = Inquiry.Priority.NORMAL

        # Generate the next inquiry code.
        last_inquiry = (
            Inquiry.objects.filter(code__startswith="INQ-").order_by("-code").first()
        )
        next_number = 1
        if last_inquiry:
            try:
                next_number = int(last_inquiry.code.split("-")[-1]) + 1
            except (ValueError, IndexError):
                pass
        code = f"INQ-{next_number:05d}"

        inquiry = Inquiry.objects.create(
            code=code,
            customer_id=data["customerId"],
            inquiry_type=data["inquiryType"],
            requirement=data["requirement"],
            quantity=data["quantity"],
            value=data["value"],
            category_id=data.get("categoryId"),
            subcategory_id=data.get("subcategoryId"),
            artist_id=data.get("artistId"),
            source=data["source"],
            priority=priority,
            status=Inquiry.Status.TOUCHBASE,
            rm_id=rm_id,
            assigned_on=timezone.now() if rm_id else None,
            notes=data.get("notes", ""),
            expected_timeline=data.get("expectedTimeline", ""),
            budget_range=data.get("budgetRange", ""),
            art_style=data.get("artStyle", ""),
        )

        InquiryActivity.objects.create(
            inquiry=inquiry,
            action="created",
            description="Inquiry created",
            metadata={
                "code": inquiry.code,
                "status": inquiry.status,
                "source": inquiry.source,
            },
            created_by=user,
        )

        inquiry = self.get_queryset(request, apply_tab=False, apply_status=False).get(
            pk=inquiry.pk
        )

        return Response(InquiryListSerializer(inquiry).data, status=201)


class InquiryAssignView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/assign/
    Payload: {"rmId": "<uuid>", "priority": "High"}   (priority optional)
    Returns the full inquiry, same shape as GET /inquiries/{id}/.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        if not (user.is_admin or user.can("inquiries", "assignRm")):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = InquiryAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)
            rm = User.objects.get(pk=data["rmId"])

            metadata = {}

            if str(inquiry.rm_id) != str(rm.id):
                metadata["previousRmId"] = str(inquiry.rm_id) if inquiry.rm_id else None
                metadata["rmId"] = str(rm.id)
                metadata["rmName"] = rm.name
                inquiry.rm = rm
                inquiry.assigned_on = timezone.now()

            new_priority = data.get("priority")
            if new_priority and new_priority != inquiry.priority:
                metadata["previousPriority"] = inquiry.priority
                metadata["priority"] = new_priority
                inquiry.priority = new_priority

            if metadata:
                inquiry.save()

                parts = []
                if "rmId" in metadata:
                    parts.append(f"Assigned to {rm.name}")
                if "priority" in metadata:
                    parts.append(f"Priority set to {metadata['priority']}")

                InquiryActivity.objects.create(
                    inquiry=inquiry,
                    action="assigned",
                    description=" · ".join(parts),
                    metadata=metadata,
                    created_by=user,
                )

        # Re-fetch with the repeat_prospect annotation, as the other views do.
        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)


class InquiryBulkView(APIView):
    """
    POST /api/v1/crm/inquiries/bulk/
    Payload:  {"ids": [...], "action": "reassign", "rmId": "<uuid>"}
    Response: {"updated": <number of inquiries actually changed>}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not (user.is_admin or user.can("inquiries", "assignRm")):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = InquiryBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ids = data["ids"]
        rm = User.objects.get(pk=data["rmId"])
        updated = 0

        with transaction.atomic():
            inquiries = list(Inquiry.objects.select_for_update().filter(pk__in=ids))

            # All-or-nothing: every id must exist.
            missing = set(ids) - {i.pk for i in inquiries}
            if missing:
                return Response(
                    {
                        "ids": [
                            "Inquiries not found: "
                            + ", ".join(str(m) for m in sorted(missing, key=str))
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()
            for inquiry in inquiries:
                if str(inquiry.rm_id) == str(rm.id):
                    continue  # already assigned to this RM, nothing to change

                previous_rm_id = str(inquiry.rm_id) if inquiry.rm_id else None
                inquiry.rm = rm
                inquiry.assigned_on = now
                inquiry.save()

                InquiryActivity.objects.create(
                    inquiry=inquiry,
                    action="assigned",
                    description=f"Assigned to {rm.name}",
                    metadata={
                        "previousRmId": previous_rm_id,
                        "rmId": str(rm.id),
                        "rmName": rm.name,
                        "bulk": True,
                    },
                    created_by=user,
                )
                updated += 1

        return Response({"updated": updated})


class InquiryStatusView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/status/
    Payload:  {"status": "Lost", "remark": "Budget not approved"}
    Response: the full inquiry (same shape as GET /inquiries/{id}/)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquiryStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        remark = serializer.validated_data["remark"]

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            # Admin, or the RM this inquiry is assigned to.
            if not user.is_admin and inquiry.rm_id != user.id:
                raise PermissionDenied("You do not have permission to do this.")

            if inquiry.status != new_status:
                previous_status = inquiry.status
                inquiry.status = new_status

                if new_status in (Inquiry.Status.WON, Inquiry.Status.LOST):
                    inquiry.closed_at = timezone.now()
                    inquiry.next_follow_up = None
                else:
                    inquiry.closed_at = None

                inquiry.save()

                description = f"Status changed from {previous_status} to {new_status}"
                if remark:
                    description += f": {remark}"

                InquiryActivity.objects.create(
                    inquiry=inquiry,
                    action="status_changed",
                    description=description[:500],
                    metadata={
                        "previousStatus": previous_status,
                        "status": new_status,
                        "remark": remark,
                    },
                    created_by=user,
                )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)


class InquiryDetailView(APIView):

    # Request key -> model field (used by PATCH)
    FIELD_MAP = {
        "customerId": "customer_id",
        "inquiryType": "inquiry_type",
        "requirement": "requirement",
        "quantity": "quantity",
        "value": "value",
        "categoryId": "category_id",
        "subcategoryId": "subcategory_id",
        "artistId": "artist_id",
        "source": "source",
        "notes": "notes",
        "expectedTimeline": "expected_timeline",
        "budgetRange": "budget_range",
        "artStyle": "art_style",
    }

    def _queryset(self, request):
        queryset = Inquiry.objects.select_related(
            "customer", "category", "subcategory", "artist", "rm"
        ).annotate(
            repeat_prospect=Exists(
                Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                    pk=OuterRef("pk")
                )
            )
        )

        # Admin can access all inquiries.
        # RM can only access inquiries assigned to them.
        if not request.user.is_admin:
            queryset = queryset.filter(rm=request.user)

        return queryset

    def get(self, request, pk):
        inquiry = get_object_or_404(self._queryset(request), pk=pk)
        return Response(InquiryListSerializer(inquiry).data)

    def put(self, request, pk):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        inquiry = get_object_or_404(self._queryset(request), pk=pk)

        can_assign_rm = user.is_admin or user.can("inquiries", "assignRm")

        if can_assign_rm:
            rm_id = data.get("rmId")
            priority = data.get("priority", Inquiry.Priority.NORMAL)
        else:
            rm_id = user.id
            priority = Inquiry.Priority.NORMAL

        # Update all editable fields.
        inquiry.customer_id = data["customerId"]
        inquiry.inquiry_type = data["inquiryType"]
        inquiry.requirement = data["requirement"]
        inquiry.quantity = data["quantity"]
        inquiry.value = data["value"]
        inquiry.category_id = data.get("categoryId")
        inquiry.subcategory_id = data.get("subcategoryId")
        inquiry.artist_id = data.get("artistId")
        inquiry.source = data["source"]
        inquiry.priority = priority
        inquiry.notes = data.get("notes", "")
        inquiry.expected_timeline = data.get("expectedTimeline", "")
        inquiry.budget_range = data.get("budgetRange", "")
        inquiry.art_style = data.get("artStyle", "")

        if str(inquiry.rm_id) != str(rm_id):
            inquiry.rm_id = rm_id
            inquiry.assigned_on = timezone.now() if rm_id else None

        inquiry.save()

        inquiry = get_object_or_404(self._queryset(request), pk=pk)
        return Response(InquiryListSerializer(inquiry).data)

    def patch(self, request, pk):
        user = request.user
        inquiry = get_object_or_404(self._queryset(request), pk=pk)

        serializer = InquiryCreateSerializer(
            data=request.data,
            partial=True,
            context={"instance": inquiry},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Only the fields that were sent are changed.
        for key, field in self.FIELD_MAP.items():
            if key in data:
                setattr(inquiry, field, data[key])

        can_assign_rm = user.is_admin or user.can("inquiries", "assignRm")

        if can_assign_rm and "priority" in data:
            inquiry.priority = data["priority"]

        if can_assign_rm and "rmId" in data:
            new_rm = data["rmId"]
            if str(inquiry.rm_id) != str(new_rm):
                inquiry.rm_id = new_rm
                inquiry.assigned_on = timezone.now() if new_rm else None

        inquiry.save()

        inquiry = get_object_or_404(self._queryset(request), pk=pk)
        return Response(InquiryListSerializer(inquiry).data)


class InquiryCountsView(InquiryListView):
    """
    Return tab counts for the Admin inquiry screen.
    Honors q, priority, source, rmId, customerId, valueBand and dateRange,
    but NOT the selected tab or status, so every badge shows its own total.
    """

    # Inherits from InquiryListView, so block POST (it would create an inquiry)
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        queryset = self.get_queryset(
            request,
            apply_tab=False,
            apply_status=False,
            with_repeat=False,
        ).order_by()  # ordering isn't needed for counts

        S = Inquiry.Status
        today = timezone.localdate()

        return Response(
            queryset.aggregate(
                all=Count("id"),
                unassigned=Count("id", filter=Q(rm__isnull=True)),
                assigned=Count("id", filter=Q(rm__isnull=False)),
                today=Count("id", filter=Q(next_follow_up__date=today)),
                touchbase=Count("id", filter=Q(status=S.TOUCHBASE)),
                followup=Count("id", filter=Q(status=S.TOUCHBASE_FOLLOWUP)),
                active=Count("id", filter=Q(status=S.ACTIVE_CONVERSATIONS)),
                nurture=Count("id", filter=Q(status=S.NURTURE)),
                won=Count("id", filter=Q(status=S.WON)),
                lost=Count("id", filter=Q(status=S.LOST)),
            )
        )


class InquiryActivityListView(APIView):

    def get(self, request, pk):
        queryset = Inquiry.objects.all()

        # RMs can only view activities for their own inquiries
        if not request.user.is_admin:
            queryset = queryset.filter(rm=request.user)

        inquiry = get_object_or_404(queryset, pk=pk)

        activities = InquiryActivity.objects.filter(inquiry=inquiry).select_related(
            "created_by"
        )

        serializer = InquiryActivitySerializer(activities, many=True)

        return Response(serializer.data)


class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _base_queryset():
        return (
            Customer.objects.select_related("rm")
            .annotate(
                total_inquiries=Count("inquiries"),
                open_inquiries=Count(
                    "inquiries",
                    filter=~Q(
                        inquiries__status__in=[Inquiry.Status.WON, Inquiry.Status.LOST]
                    ),
                ),
                won_inquiries=Count(
                    "inquiries", filter=Q(inquiries__status=Inquiry.Status.WON)
                ),
                total_value=Sum("inquiries__value"),
                last_activity_at=Max("inquiries__updated_at"),
            )
            .prefetch_related(
                Prefetch(
                    "inquiries",
                    queryset=Inquiry.objects.order_by("created_at").only(
                        "id", "code", "customer_id", "created_at"
                    ),
                    to_attr="first_inquiry",
                )
            )
        )

    def get(self, request):
        if not request.user.can("customers", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        params = request.query_params
        queryset = self._base_queryset()

        search = params.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(code__icontains=search)
            )

        if params.get("customerType"):
            queryset = queryset.filter(customer_type=params["customerType"])
        if params.get("status"):
            queryset = queryset.filter(status=params["status"])
        if params.get("location"):
            queryset = queryset.filter(location__iexact=params["location"])
        if params.get("rmId"):
            queryset = queryset.filter(rm_id=params["rmId"])

        queryset = queryset.order_by("name")

        def _int(name, default, maximum=None):
            try:
                value = max(int(params.get(name, default)), 1)
            except (TypeError, ValueError):
                return default
            return min(value, maximum) if maximum else value

        page = _int("page", 1)
        page_size = _int("pageSize", 10, maximum=100)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        return Response(
            {
                "count": paginator.count,
                "page": page_obj.number,
                "pageSize": page_size,
                "results": CustomerListSerializer(page_obj.object_list, many=True).data,
            }
        )

    def post(self, request):
        if not request.user.can("customers", "create"):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = CustomerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()

        customer = self._base_queryset().get(pk=customer.pk)
        return Response(
            CustomerListSerializer(customer).data, status=status.HTTP_201_CREATED
        )


class CustomerLocationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.can("customers", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        locations = (
            Customer.objects.exclude(location="")
            .exclude(location__isnull=True)
            .values_list("location", flat=True)
            .distinct()
            .order_by("location")
        )

        return Response(list(locations))


class CustomerDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("customers", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            customer = Customer.objects.select_related("rm").get(pk=pk)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(CustomerListSerializer(customer).data)

    def patch(self, request, pk):
        if not request.user.can("customers", "edit"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            customer = Customer.objects.select_related("rm").get(pk=pk)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Remember the previous type before updating.
        previous_customer_type = customer.customer_type

        serializer = CustomerUpdateSerializer(
            customer,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        customer = serializer.save()

        # If changed to Customer for the first time,
        # stamp customer_since.
        if (
            customer.customer_type == "Customer"
            and previous_customer_type != "Customer"
            and customer.customer_since is None
        ):
            customer.customer_since = timezone.now()
            customer.save(update_fields=["customer_since"])

        return Response(CustomerListSerializer(customer).data)


class CustomerActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("customers", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        # Make sure the customer exists.
        try:
            Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        activities = (
            InquiryActivity.objects.filter(inquiry__customer_id=pk)
            .select_related("inquiry", "created_by")
            .order_by("-created_at")
        )

        return Response(
            CustomerActivitySerializer(
                activities,
                many=True,
            ).data
        )


class MasterOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, kind):
        if not request.user.can("masters", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        category_id = request.query_params.get("categoryId")

        if kind == "categories":
            queryset = Category.objects.filter(is_active=True).order_by("name")

            return Response(
                [
                    {
                        "id": str(obj.id),
                        "name": obj.name,
                    }
                    for obj in queryset
                ]
            )

        if kind == "subcategories":
            queryset = Subcategory.objects.filter(is_active=True).select_related(
                "category"
            )

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            return Response(
                [
                    {
                        "id": str(obj.id),
                        "name": obj.name,
                        "categoryId": str(obj.category_id),
                    }
                    for obj in queryset
                ]
            )

        if kind == "artists":
            queryset = Artist.objects.filter(is_active=True).select_related("category")

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            return Response(
                [
                    {
                        "id": str(obj.id),
                        "name": obj.name,
                        "categoryId": (
                            str(obj.category_id) if obj.category_id else None
                        ),
                    }
                    for obj in queryset
                ]
            )

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )


class MasterListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, kind):
        if not request.user.can("masters", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        q = request.query_params.get("q")
        status_filter = request.query_params.get("status")
        category_id = request.query_params.get("categoryId")

        page = max(
            int(request.query_params.get("page", 1)),
            1,
        )
        page_size = max(
            int(request.query_params.get("pageSize", 10)),
            1,
        )

        # ==================================================
        # CATEGORIES
        # ==================================================
        if kind == "categories":
            queryset = Category.objects.all()

            if q:
                queryset = queryset.filter(name__icontains=q)

            if status_filter:
                queryset = queryset.filter(
                    is_active=(status_filter.lower() == "active")
                )

            queryset = queryset.order_by("name")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            results = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "description": obj.description,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
                for obj in page_obj.object_list
            ]

        # ==================================================
        # SUBCATEGORIES
        # ==================================================
        elif kind == "subcategories":
            queryset = Subcategory.objects.select_related("category").all()

            if q:
                queryset = queryset.filter(name__icontains=q)

            if status_filter:
                queryset = queryset.filter(
                    is_active=(status_filter.lower() == "active")
                )

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            results = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": str(obj.category_id),
                    "categoryName": obj.category.name,
                    "description": obj.description,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
                for obj in page_obj.object_list
            ]

        # ==================================================
        # ARTISTS
        # ==================================================
        elif kind == "artists":
            queryset = Artist.objects.select_related("category").all()

            if q:
                queryset = queryset.filter(name__icontains=q)

            if status_filter:
                queryset = queryset.filter(
                    is_active=(status_filter.lower() == "active")
                )

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            results = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": (str(obj.category_id) if obj.category_id else None),
                    "categoryName": (obj.category.name if obj.category_id else None),
                    "nationality": obj.nationality,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
                for obj in page_obj.object_list
            ]

        else:
            return Response(
                {"detail": "Unknown master."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "count": paginator.count,
                "page": page_obj.number,
                "pageSize": page_size,
                "results": results,
            }
        )

    def post(self, request, kind):
        if not request.user.can("masters", "create"):
            raise PermissionDenied("You do not have permission to do this.")

        name = request.data.get("name", "").strip()

        if not name:
            return Response(
                {"name": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ==================================================
        # CATEGORIES
        # ==================================================
        if kind == "categories":
            if Category.objects.filter(name__iexact=name).exists():
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            category = Category.objects.create(
                name=name,
                description=request.data.get("description", ""),
                is_active=True,
            )

            return Response(
                {
                    "id": str(category.id),
                    "name": category.name,
                    "description": category.description,
                    "status": "Active",
                },
                status=status.HTTP_201_CREATED,
            )

        # ==================================================
        # SUBCATEGORIES
        # ==================================================
        if kind == "subcategories":
            category_id = request.data.get("categoryId")

            if not category_id:
                return Response(
                    {"categoryId": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                return Response(
                    {"categoryId": ["Category does not exist."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Subcategory.objects.filter(
                category=category,
                name__iexact=name,
            ).exists():
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subcategory = Subcategory.objects.create(
                name=name,
                category=category,
                description=request.data.get("description", ""),
                is_active=True,
            )

            return Response(
                {
                    "id": str(subcategory.id),
                    "name": subcategory.name,
                    "categoryId": str(subcategory.category_id),
                    "categoryName": category.name,
                    "description": subcategory.description,
                    "status": "Active",
                },
                status=status.HTTP_201_CREATED,
            )

        # ==================================================
        # ARTISTS
        # ==================================================
        if kind == "artists":
            category_id = request.data.get("categoryId")

            if not category_id:
                return Response(
                    {"categoryId": ["This field is required."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                return Response(
                    {"categoryId": ["Category does not exist."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Artist.objects.filter(
                category=category,
                name__iexact=name,
            ).exists():
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            artist = Artist.objects.create(
                name=name,
                category=category,
                nationality=request.data.get("nationality", ""),
                is_active=True,
            )

            return Response(
                {
                    "id": str(artist.id),
                    "name": artist.name,
                    "categoryId": str(artist.category_id),
                    "categoryName": category.name,
                    "nationality": artist.nationality,
                    "status": "Active",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )


class MasterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, kind, pk):
        if not request.user.can("masters", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        # ==============================================
        # CATEGORY
        # ==============================================
        if kind == "categories":
            try:
                obj = Category.objects.get(pk=pk)
            except Category.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "description": obj.description,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
            )

        # ==============================================
        # SUBCATEGORY
        # ==============================================
        if kind == "subcategories":
            try:
                obj = Subcategory.objects.select_related("category").get(pk=pk)
            except Subcategory.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": str(obj.category_id),
                    "categoryName": obj.category.name,
                    "description": obj.description,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
            )

        # ==============================================
        # ARTIST
        # ==============================================
        if kind == "artists":
            try:
                obj = Artist.objects.select_related("category").get(pk=pk)
            except Artist.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": (str(obj.category_id) if obj.category_id else None),
                    "categoryName": (obj.category.name if obj.category_id else None),
                    "nationality": obj.nationality,
                    "status": ("Active" if obj.is_active else "Inactive"),
                }
            )

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )

    def patch(self, request, kind, pk):
        if not request.user.can("masters", "edit"):
            raise PermissionDenied("You do not have permission to do this.")

        # ==================================================
        # CATEGORY
        # ==================================================
        if kind == "categories":
            try:
                obj = Category.objects.get(pk=pk)
            except Category.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            name = request.data.get("name")

            if name is not None:
                name = name.strip()

                if (
                    Category.objects.filter(name__iexact=name)
                    .exclude(pk=obj.pk)
                    .exists()
                ):
                    return Response(
                        {"name": ["This name already exists."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                obj.name = name

            if "description" in request.data:
                obj.description = request.data["description"]

            if "status" in request.data:
                obj.is_active = request.data["status"].lower() == "active"

            obj.save()

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "description": obj.description,
                    "status": "Active" if obj.is_active else "Inactive",
                }
            )

        # ==================================================
        # SUBCATEGORY
        # ==================================================
        if kind == "subcategories":
            try:
                obj = Subcategory.objects.select_related("category").get(pk=pk)
            except Subcategory.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_category = obj.category

            if "categoryId" in request.data:
                try:
                    new_category = Category.objects.get(pk=request.data["categoryId"])
                except Category.DoesNotExist:
                    return Response(
                        {"categoryId": ["Category does not exist."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            name = request.data.get("name", obj.name).strip()

            if (
                Subcategory.objects.filter(
                    category=new_category,
                    name__iexact=name,
                )
                .exclude(pk=obj.pk)
                .exists()
            ):
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj.name = name
            obj.category = new_category

            if "description" in request.data:
                obj.description = request.data["description"]

            if "status" in request.data:
                obj.is_active = request.data["status"].lower() == "active"

            obj.save()

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": str(obj.category_id),
                    "categoryName": obj.category.name,
                    "description": obj.description,
                    "status": "Active" if obj.is_active else "Inactive",
                }
            )

        # ==================================================
        # ARTIST
        # ==================================================
        if kind == "artists":
            try:
                obj = Artist.objects.select_related("category").get(pk=pk)
            except Artist.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_category = obj.category

            if "categoryId" in request.data:
                try:
                    new_category = Category.objects.get(pk=request.data["categoryId"])
                except Category.DoesNotExist:
                    return Response(
                        {"categoryId": ["Category does not exist."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            name = request.data.get("name", obj.name).strip()

            if (
                Artist.objects.filter(
                    category=new_category,
                    name__iexact=name,
                )
                .exclude(pk=obj.pk)
                .exists()
            ):
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj.name = name
            obj.category = new_category

            if "nationality" in request.data:
                obj.nationality = request.data["nationality"]

            if "status" in request.data:
                obj.is_active = request.data["status"].lower() == "active"

            obj.save()

            return Response(
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": str(obj.category_id),
                    "categoryName": obj.category.name,
                    "nationality": obj.nationality,
                    "status": "Active" if obj.is_active else "Inactive",
                }
            )

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )


class InquiryWonView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/won/
    Marks the inquiry as Won and creates its sale.
    Returns the full inquiry with `sale` filled in.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquiryWonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            # Admin, or the RM this inquiry is assigned to.
            if not user.is_admin and inquiry.rm_id != user.id:
                raise PermissionDenied("You do not have permission to do this.")

            if Sale.objects.filter(inquiry=inquiry).exists():
                return Response(
                    {"detail": "A sale already exists for this inquiry."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            last_sale = (
                Sale.objects.filter(code__startswith="SAL-").order_by("-code").first()
            )
            next_number = 1
            if last_sale:
                try:
                    next_number = int(last_sale.code.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    pass

            sale = Sale.objects.create(
                code=f"SAL-{next_number:05d}",
                inquiry=inquiry,
                total_value=data["totalValue"],
                sale_date=data["saleDate"],
                certificate_plan=data.get("certificatePlan", ""),
                shipment_priority=data.get("shipmentPriority", "Normal"),
                required_shipment_date=data.get("requiredShipmentDate"),
                shipment_instructions=data.get("shipmentInstructions", ""),
                payment_status=data.get("paymentStatus", "Pending"),
                payment_notes=data.get("paymentNotes", ""),
                notes=data.get("notes", ""),
                created_by=user,
            )

            SaleProduct.objects.bulk_create(
                [
                    SaleProduct(
                        sale=sale,
                        name=p["name"],
                        artist_id=p.get("artistId"),
                        url=p.get("url"),
                        listed_price=p["listedPrice"],
                        quantity=p.get("quantity", 1),
                        product_status=p.get("productStatus", ""),
                        commission_ready_date=p.get("commissionReadyDate"),
                        order_notes=p.get("orderNotes", ""),
                    )
                    for p in data["products"]
                ]
            )

            previous_status = inquiry.status
            inquiry.status = Inquiry.Status.WON
            inquiry.closed_at = timezone.now()
            inquiry.next_follow_up = None
            inquiry.save()

            InquiryActivity.objects.create(
                inquiry=inquiry,
                action="won",
                description=f"Marked as Won, sale {sale.code} created",
                metadata={
                    "previousStatus": previous_status,
                    "saleId": str(sale.id),
                    "saleCode": sale.code,
                    "totalValue": str(sale.total_value),
                },
                created_by=user,
            )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(
            InquiryListSerializer(inquiry).data, status=status.HTTP_201_CREATED
        )


class CustomerSalesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("customers", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        if not Customer.objects.filter(pk=pk).exists():
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sales = (
            Sale.objects.filter(inquiry__customer_id=pk)
            .select_related("inquiry")
            .prefetch_related("products")
            .order_by("-sale_date", "-created_at")
        )

        return Response(CustomerSaleSerializer(sales, many=True).data)


def _iso_utc(value):
    return value.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


class InquiryTouchbaseView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/touchbase/
    Body: {"method": "Call", "at": "<ISO-8601 UTC>", "notes": "..."}
    Records the FIRST outreach. Permission: the inquiry's own RM.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquiryTouchbaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        method = data["method"]
        at = data["at"].astimezone(dt_timezone.utc)
        notes = (data.get("notes") or "").strip()

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            if not user.is_admin and inquiry.rm_id != user.id:
                raise PermissionDenied("You do not have permission to do this.")

            if InquiryActivity.objects.filter(
                inquiry=inquiry, action="touchbase"
            ).exists():
                return Response(
                    {
                        "detail": "A touchbase has already been recorded for this inquiry."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if inquiry.status != Inquiry.Status.TOUCHBASE:
                return Response(
                    {
                        "detail": "A touchbase can only be recorded for an inquiry in Touchbase status."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            next_follow_up = at + timedelta(days=2)

            inquiry.status = Inquiry.Status.TOUCHBASE_FOLLOWUP
            inquiry.last_contact = at
            inquiry.next_follow_up = next_follow_up
            inquiry.save()

            description = f"Touchbase recorded via {method}"
            if notes:
                description += f": {notes}"

            InquiryActivity.objects.create(
                inquiry=inquiry,
                action="touchbase",
                description=description[:500],
                metadata={
                    "method": method,
                    "at": _iso_utc(at),
                    "nextFollowUp": _iso_utc(next_follow_up),
                    "notes": notes,
                },
                created_by=user,
            )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)


_S = Inquiry.Status
INTERACTION_MOVES = {
    _S.TOUCHBASE_FOLLOWUP.value: {
        _S.ACTIVE_CONVERSATIONS.value,
        _S.NURTURE.value,
        _S.LOST.value,
    },
    _S.ACTIVE_CONVERSATIONS.value: {
        _S.NURTURE.value,
        _S.WON.value,
        _S.LOST.value,
    },
}


class InquiryInteractionView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/interactions/
    Body: method*, at*, nextFollowUp, notes, moveTo
    Records a follow-up or conversation; optionally moves the status.
    Permission: the inquiry's own RM.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquiryInteractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        method = data["method"]
        at = data["at"].astimezone(dt_timezone.utc)
        notes = (data.get("notes") or "").strip()
        move_to = data.get("moveTo")
        next_follow_up = data.get("nextFollowUp")

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            if inquiry.rm_id != user.id:
                raise PermissionDenied("You do not have permission to do this.")

            allowed_moves = INTERACTION_MOVES.get(inquiry.status)
            if allowed_moves is None:
                return Response(
                    {
                        "detail": "An interaction can only be recorded for an inquiry "
                        "in Touchbase Follow-up or Active Conversations status."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if move_to and move_to not in allowed_moves:
                return Response(
                    {"moveTo": [f"Cannot move from {inquiry.status} to {move_to}."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            kind = (
                "Follow-up"
                if inquiry.status == _S.TOUCHBASE_FOLLOWUP.value
                else "Conversation"
            )
            previous_status = inquiry.status

            inquiry.last_contact = at
            inquiry.next_follow_up = next_follow_up
            if move_to:
                inquiry.status = move_to
            if move_to in (_S.WON.value, _S.LOST.value):
                inquiry.closed_at = timezone.now()
            inquiry.save()

            description = f"{kind} via {method}"
            if move_to:
                description += f" · moved to {move_to}"
            if notes:
                description += f": {notes}"

            InquiryActivity.objects.create(
                inquiry=inquiry,
                action=kind,
                description=description[:500],
                metadata={
                    "method": method,
                    "at": _iso_utc(at),
                    "nextFollowUp": (
                        _iso_utc(next_follow_up) if next_follow_up else None
                    ),
                    "notes": notes,
                    "moveTo": move_to,
                    "previousStatus": previous_status,
                },
                created_by=user,
            )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)


SNOOZABLE_STATUSES = (
    _S.TOUCHBASE_FOLLOWUP.value,
    _S.ACTIVE_CONVERSATIONS.value,
)


class InquirySnoozeView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/snooze/
    Body: {"nextFollowUp": "<ISO-8601 UTC>"}
    Pushes the next follow-up date. Permission: the inquiry's own RM.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquirySnoozeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_follow_up = serializer.validated_data["nextFollowUp"].astimezone(
            dt_timezone.utc
        )

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            if inquiry.rm_id != user.id:
                raise PermissionDenied(
                    "Only the RM assigned to this inquiry can do this."
                )

            if inquiry.status not in SNOOZABLE_STATUSES:
                return Response(
                    {
                        "detail": "Only an inquiry in Touchbase Follow-up or "
                        "Active Conversations status can be snoozed."
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            previous = inquiry.next_follow_up
            inquiry.next_follow_up = new_follow_up
            inquiry.save()

            InquiryActivity.objects.create(
                inquiry=inquiry,
                action="snoozed",
                description=f"Follow-up snoozed to {_iso_utc(new_follow_up)}"[:500],
                metadata={
                    "previousNextFollowUp": _iso_utc(previous) if previous else None,
                    "nextFollowUp": _iso_utc(new_follow_up),
                },
                created_by=user,
            )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)


class InquiryStatusView(APIView):
    """
    POST /api/v1/crm/inquiries/{id}/status/
    Body: status*, notes, nextFollowUp
    Admin-type users: inquiries.edit. RM: own Nurture inquiry -> Active Conversations only.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user

        serializer = InquiryStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        new_status = data["status"]
        notes = (data.get("notes") or "").strip()
        is_rm = user.role_id == RM_ROLE_ID

        with transaction.atomic():
            inquiry = get_object_or_404(Inquiry.objects.select_for_update(), pk=pk)

            if is_rm:
                if (
                    inquiry.rm_id != user.id
                    or inquiry.status != Inquiry.Status.NURTURE
                    or new_status != Inquiry.Status.ACTIVE_CONVERSATIONS
                ):
                    raise PermissionDenied(
                        "You can only move a Nurture inquiry back to Active Conversations."
                    )
                if data.get("nextFollowUp") is None:
                    return Response(
                        {"nextFollowUp": ["This field is required."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif not user.can("inquiries", "edit"):
                raise PermissionDenied("You do not have permission to do this.")

            if inquiry.status in (Inquiry.Status.WON, Inquiry.Status.LOST):
                return Response(
                    {"detail": "Inquiry is already closed."},
                    status=status.HTTP_409_CONFLICT,
                )
            if inquiry.status == new_status:
                return Response(
                    {"detail": f"Inquiry is already in {new_status} status."},
                    status=status.HTTP_409_CONFLICT,
                )

            previous_status = inquiry.status
            inquiry.status = new_status

            if new_status == Inquiry.Status.ACTIVE_CONVERSATIONS:
                if data.get("nextFollowUp"):
                    inquiry.next_follow_up = data["nextFollowUp"]
            else:
                inquiry.next_follow_up = None  # Won / Lost / Nurture

            if new_status in (Inquiry.Status.WON, Inquiry.Status.LOST):
                inquiry.closed_at = timezone.now()
            inquiry.save()

            if new_status == Inquiry.Status.WON:
                customer = inquiry.customer
                fields = []
                if customer.customer_type != "Customer":
                    customer.customer_type = "Customer"
                    fields.append("customer_type")
                if customer.customer_since is None:
                    customer.customer_since = timezone.now()
                    fields.append("customer_since")
                if fields:
                    customer.save(update_fields=fields + ["updated_at"])

            description = f"Status changed from {previous_status} to {new_status}"
            if notes:
                description += f": {notes}"
            InquiryActivity.objects.create(
                inquiry=inquiry,
                action="status_changed",
                description=description[:500],
                metadata={
                    "previousStatus": previous_status,
                    "status": new_status,
                    "notes": notes,
                },
                created_by=user,
            )

        inquiry = (
            Inquiry.objects.select_related(
                "customer", "category", "subcategory", "artist", "rm"
            )
            .annotate(
                repeat_prospect=Exists(
                    Inquiry.objects.filter(customer_id=OuterRef("customer_id")).exclude(
                        pk=OuterRef("pk")
                    )
                )
            )
            .get(pk=pk)
        )
        return Response(InquiryListSerializer(inquiry).data)
