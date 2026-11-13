from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from .models import Inquiry, InquiryActivity
from .serializers import InquiryListSerializer, InquiryCreateSerializer, InquiryActivitySerializer
from inquiries.models import Customer,Category, Subcategory, Artist
from inquiries.serializers import CustomerListSerializer,CustomerCreateSerializer, CustomerUpdateSerializer,CustomerActivitySerializer
from rest_framework import status



class InquiryListView(APIView):

    def get_queryset(self, request, apply_tab=True):
        user = request.user

        queryset = (
            Inquiry.objects
            .select_related(
                "customer",
                "category",
                "subcategory",
                "artist",
                "rm",
            )
        )

        # RM users can only see their own inquiries.
        if not user.is_admin:
            queryset = queryset.filter(rm=user)

        # Tab filtering
        tab = request.query_params.get("tab", "all")

                # Tab filtering
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
            tab = request.query_params.get("tab", "all")

            if tab == "today":
                today = timezone.localdate()
                queryset = queryset.filter(
                    next_follow_up__date=today
                )
            elif tab in tab_filters:
                queryset = queryset.filter(tab_filters[tab])

        # Search
        q = request.query_params.get("q")
        if q:
            queryset = queryset.filter(
                Q(customer__name__icontains=q)
                | Q(customer__email__icontains=q)
                | Q(customer__phone__icontains=q)
                | Q(code__icontains=q)
            )

        # Priority filter
        priority = request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)

        # Source filter
        source = request.query_params.get("source")
        if source:
            queryset = queryset.filter(source=source)

        # Date range
        date_range = request.query_params.get("dateRange")
        if date_range:
            try:
                days = int(date_range)
                if days > 0:
                    start_date = timezone.now() - timedelta(days=days)
                    queryset = queryset.filter(
                        created_at__gte=start_date
                    )
            except ValueError:
                pass

        # Ordering
        ordering = request.query_params.get(
            "ordering",
            "-createdAt",
        )

        ordering_map = {
            "createdAt": "created_at",
            "-createdAt": "-created_at",
            "nextFollowUp": "next_follow_up",
            "-nextFollowUp": "-next_follow_up",
            "value": "value",
            "-value": "-value",
        }

        return queryset.order_by(
            ordering_map.get(ordering, "-created_at")
        )

    
    def post(self, request):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        can_assign_rm = (
            user.is_admin
            or user.permissions.get("inquiries", {}).get("assignRm", False)
        )

        if can_assign_rm:
            rm_id = data.get("rmId")
            priority = data.get("priority", Inquiry.Priority.MEDIUM)
        else:
            rm_id = user.id
            priority = Inquiry.Priority.MEDIUM

        # Generate the next inquiry code.
        last_inquiry = (
            Inquiry.objects
            .filter(code__startswith="INQ-")
            .order_by("-code")
            .first()
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
            category_id=data["categoryId"],
            subcategory_id=data["subcategoryId"],
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
        inquiry = (
            Inquiry.objects
            .select_related(
                "customer",
                "category",
                "subcategory",
                "artist",
                "rm",
            )
            .get(pk=inquiry.pk)
        )

        return Response(
            InquiryListSerializer(inquiry).data,
            status=201,
        )



class InquiryDetailView(APIView):

    def get(self, request, pk):
        queryset = (
            Inquiry.objects
            .select_related(
                "customer",
                "category",
                "subcategory",
                "artist",
                "rm",
            )
        )

        # Admin can view all inquiries.
        # RM can only view inquiries assigned to them.
        if not request.user.is_admin:
            queryset = queryset.filter(rm=request.user)

        inquiry = get_object_or_404(queryset, pk=pk)

        return Response(
            InquiryListSerializer(inquiry).data
        )

    def put(self, request, pk):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user = request.user

        queryset = Inquiry.objects.all()

        if not user.is_admin:
            queryset = queryset.filter(rm=user)

        inquiry = get_object_or_404(queryset, pk=pk)

        can_assign_rm = (
            user.is_admin
            or user.permissions.get("inquiries", {}).get("assignRm", False)
        )

        if can_assign_rm:
            rm_id = data.get("rmId")
            priority = data.get("priority", Inquiry.Priority.MEDIUM)
        else:
            rm_id = user.id
            priority = Inquiry.Priority.MEDIUM

        # Update all editable fields.
        inquiry.customer_id = data["customerId"]
        inquiry.inquiry_type = data["inquiryType"]
        inquiry.requirement = data["requirement"]
        inquiry.quantity = data["quantity"]
        inquiry.value = data["value"]
        inquiry.category_id = data["categoryId"]
        inquiry.subcategory_id = data["subcategoryId"]
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

        inquiry = (
            Inquiry.objects
            .select_related(
                "customer",
                "category",
                "subcategory",
                "artist",
                "rm",
            )
            .get(pk=inquiry.pk)
        )

        return Response(InquiryListSerializer(inquiry).data)


class InquiryCountsView(InquiryListView):
    """
    Return tab counts for the Admin inquiry screen.
    """

    def get(self, request):
        # Apply search and other filters, but NOT the selected tab.
        queryset = self.get_queryset(request, apply_tab=False)

        return Response({
            "all": queryset.count(),
            "unassigned": queryset.filter(rm__isnull=True).count(),
            "assigned": queryset.filter(rm__isnull=False).count(),
            "today": queryset.filter(
                next_follow_up__date=timezone.localdate()
            ).count(),
            "touchbase": queryset.filter(
                status=Inquiry.Status.TOUCHBASE
            ).count(),
            "followup": queryset.filter(
                status=Inquiry.Status.TOUCHBASE_FOLLOWUP
            ).count(),
            "active": queryset.filter(
                status=Inquiry.Status.ACTIVE_CONVERSATIONS
            ).count(),
            "nurture": queryset.filter(
                status=Inquiry.Status.NURTURE
            ).count(),
            "won": queryset.filter(
                status=Inquiry.Status.WON
            ).count(),
            "lost": queryset.filter(
                status=Inquiry.Status.LOST
            ).count(),
        })

class InquiryActivityListView(APIView):

    def get(self, request, pk):
        queryset = Inquiry.objects.all()

        # RMs can only view activities for their own inquiries
        if not request.user.is_admin:
            queryset = queryset.filter(rm=request.user)

        inquiry = get_object_or_404(queryset, pk=pk)

        activities = (
            InquiryActivity.objects
            .filter(inquiry=inquiry)
            .select_related("created_by")
        )

        serializer = InquiryActivitySerializer(
            activities,
            many=True
        )

        return Response(serializer.data)


class CustomerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.can("customers", "view"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        queryset = (
            Customer.objects
            .select_related("rm")
            .all()
        )

        # Search
        search = request.query_params.get("q")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(code__icontains=search)
            )

        # Filters
        customer_type = request.query_params.get("customerType")
        if customer_type:
            queryset = queryset.filter(
                customer_type=customer_type
            )

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(
                status=status_filter
            )

        location = request.query_params.get("location")
        if location:
            queryset = queryset.filter(
                location__iexact=location
            )

        queryset = queryset.order_by("name")

        # Pagination
        page = max(
            int(request.query_params.get("page", 1)),
            1,
        )
        page_size = max(
            int(request.query_params.get("pageSize", 10)),
            1,
        )

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = CustomerListSerializer(
            page_obj.object_list,
            many=True,
        )

        return Response({
            "count": paginator.count,
            "page": page_obj.number,
            "pageSize": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        if not request.user.can("customers", "create"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        serializer = CustomerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = serializer.save()

        customer = (
            Customer.objects
            .select_related("rm")
            .get(pk=customer.pk)
        )

        return Response(
            CustomerListSerializer(customer).data,
            status=status.HTTP_201_CREATED,
        )

class CustomerLocationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.can("customers", "view"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        locations = (
            Customer.objects
            .exclude(location="")
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
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        try:
            customer = (
                Customer.objects
                .select_related("rm")
                .get(pk=pk)
            )
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            CustomerListSerializer(customer).data
        )

    def patch(self, request, pk):
        if not request.user.can("customers", "edit"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        try:
            customer = (
                Customer.objects
                .select_related("rm")
                .get(pk=pk)
            )
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

        return Response(
            CustomerListSerializer(customer).data
        )

class CustomerActivitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("customers", "view"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        # Make sure the customer exists.
        try:
            Customer.objects.get(pk=pk)
        except Customer.DoesNotExist:
            return Response(
                {"detail": "Customer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        activities = (
            InquiryActivity.objects
            .filter(inquiry__customer_id=pk)
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
            raise PermissionDenied(
                "You do not have permission to do this."
            )

        category_id = request.query_params.get("categoryId")

        if kind == "categories":
            queryset = (
                Category.objects
                .filter(is_active=True)
                .order_by("name")
            )

            return Response([
                {
                    "id": str(obj.id),
                    "name": obj.name,
                }
                for obj in queryset
            ])

        if kind == "subcategories":
            queryset = (
                Subcategory.objects
                .filter(is_active=True)
                .select_related("category")
            )

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            return Response([
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": str(obj.category_id),
                }
                for obj in queryset
            ])

        if kind == "artists":
            queryset = (
                Artist.objects
                .filter(is_active=True)
                .select_related("category")
            )

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            queryset = queryset.order_by("name")

            return Response([
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": (
                        str(obj.category_id)
                        if obj.category_id else None
                    ),
                }
                for obj in queryset
            ])

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )


class MasterListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, kind):
        if not request.user.can("masters", "view"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

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
                queryset = queryset.filter(
                    name__icontains=q
                )

            if status_filter:
                queryset = queryset.filter(
                    is_active=(
                        status_filter.lower() == "active"
                    )
                )

            queryset = queryset.order_by("name")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            results = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "description": obj.description,
                    "status": (
                        "Active"
                        if obj.is_active
                        else "Inactive"
                    ),
                }
                for obj in page_obj.object_list
            ]

        # ==================================================
        # SUBCATEGORIES
        # ==================================================
        elif kind == "subcategories":
            queryset = (
                Subcategory.objects
                .select_related("category")
                .all()
            )

            if q:
                queryset = queryset.filter(
                    name__icontains=q
                )

            if status_filter:
                queryset = queryset.filter(
                    is_active=(
                        status_filter.lower() == "active"
                    )
                )

            if category_id:
                queryset = queryset.filter(
                    category_id=category_id
                )

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
                    "status": (
                        "Active"
                        if obj.is_active
                        else "Inactive"
                    ),
                }
                for obj in page_obj.object_list
            ]

        # ==================================================
        # ARTISTS
        # ==================================================
        elif kind == "artists":
            queryset = (
                Artist.objects
                .select_related("category")
                .all()
            )

            if q:
                queryset = queryset.filter(
                    name__icontains=q
                )

            if status_filter:
                queryset = queryset.filter(
                    is_active=(
                        status_filter.lower() == "active"
                    )
                )

            if category_id:
                queryset = queryset.filter(
                    category_id=category_id
                )

            queryset = queryset.order_by("name")

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)

            results = [
                {
                    "id": str(obj.id),
                    "name": obj.name,
                    "categoryId": (
                        str(obj.category_id)
                        if obj.category_id
                        else None
                    ),
                    "categoryName": (
                        obj.category.name
                        if obj.category_id
                        else None
                    ),
                    "nationality": obj.nationality,
                    "status": (
                        "Active"
                        if obj.is_active
                        else "Inactive"
                    ),
                }
                for obj in page_obj.object_list
            ]

        else:
            return Response(
                {"detail": "Unknown master."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "count": paginator.count,
            "page": page_obj.number,
            "pageSize": page_size,
            "results": results,
        })

    def post(self, request, kind):
        if not request.user.can("masters", "create"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

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
            if Category.objects.filter(
                name__iexact=name
            ).exists():
                return Response(
                    {
                        "name": [
                            "This name already exists."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            category = Category.objects.create(
                name=name,
                description=request.data.get(
                    "description",
                    ""
                ),
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
                    {
                        "categoryId": [
                            "This field is required."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                return Response(
                    {
                        "categoryId": [
                            "Category does not exist."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Subcategory.objects.filter(
                category=category,
                name__iexact=name,
            ).exists():
                return Response(
                    {
                        "name": [
                            "This name already exists."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            subcategory = Subcategory.objects.create(
                name=name,
                category=category,
                description=request.data.get(
                    "description",
                    ""
                ),
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
                    {
                        "categoryId": [
                            "This field is required."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                return Response(
                    {
                        "categoryId": [
                            "Category does not exist."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Artist.objects.filter(
                category=category,
                name__iexact=name,
            ).exists():
                return Response(
                    {
                        "name": [
                            "This name already exists."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            artist = Artist.objects.create(
                name=name,
                category=category,
                nationality=request.data.get(
                    "nationality",
                    ""
                ),
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
            raise PermissionDenied(
                "You do not have permission to do this."
            )

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

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "description": obj.description,
                "status": (
                    "Active" if obj.is_active else "Inactive"
                ),
            })

        # ==============================================
        # SUBCATEGORY
        # ==============================================
        if kind == "subcategories":
            try:
                obj = (
                    Subcategory.objects
                    .select_related("category")
                    .get(pk=pk)
                )
            except Subcategory.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "categoryId": str(obj.category_id),
                "categoryName": obj.category.name,
                "description": obj.description,
                "status": (
                    "Active" if obj.is_active else "Inactive"
                ),
            })

        # ==============================================
        # ARTIST
        # ==============================================
        if kind == "artists":
            try:
                obj = (
                    Artist.objects
                    .select_related("category")
                    .get(pk=pk)
                )
            except Artist.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "categoryId": (
                    str(obj.category_id)
                    if obj.category_id else None
                ),
                "categoryName": (
                    obj.category.name
                    if obj.category_id else None
                ),
                "nationality": obj.nationality,
                "status": (
                    "Active" if obj.is_active else "Inactive"
                ),
            })

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )

    def patch(self, request, kind, pk):
        if not request.user.can("masters", "edit"):
            raise PermissionDenied(
                "You do not have permission to do this."
            )

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

                if Category.objects.filter(
                    name__iexact=name
                ).exclude(pk=obj.pk).exists():
                    return Response(
                        {"name": ["This name already exists."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                obj.name = name

            if "description" in request.data:
                obj.description = request.data["description"]

            if "status" in request.data:
                obj.is_active = (
                    request.data["status"].lower() == "active"
                )

            obj.save()

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "description": obj.description,
                "status": "Active" if obj.is_active else "Inactive",
            })

        # ==================================================
        # SUBCATEGORY
        # ==================================================
        if kind == "subcategories":
            try:
                obj = (
                    Subcategory.objects
                    .select_related("category")
                    .get(pk=pk)
                )
            except Subcategory.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_category = obj.category

            if "categoryId" in request.data:
                try:
                    new_category = Category.objects.get(
                        pk=request.data["categoryId"]
                    )
                except Category.DoesNotExist:
                    return Response(
                        {
                            "categoryId": [
                                "Category does not exist."
                            ]
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            name = request.data.get("name", obj.name).strip()

            if Subcategory.objects.filter(
                category=new_category,
                name__iexact=name,
            ).exclude(pk=obj.pk).exists():
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj.name = name
            obj.category = new_category

            if "description" in request.data:
                obj.description = request.data["description"]

            if "status" in request.data:
                obj.is_active = (
                    request.data["status"].lower() == "active"
                )

            obj.save()

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "categoryId": str(obj.category_id),
                "categoryName": obj.category.name,
                "description": obj.description,
                "status": "Active" if obj.is_active else "Inactive",
            })

        # ==================================================
        # ARTIST
        # ==================================================
        if kind == "artists":
            try:
                obj = (
                    Artist.objects
                    .select_related("category")
                    .get(pk=pk)
                )
            except Artist.DoesNotExist:
                return Response(
                    {"detail": "Record not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            new_category = obj.category

            if "categoryId" in request.data:
                try:
                    new_category = Category.objects.get(
                        pk=request.data["categoryId"]
                    )
                except Category.DoesNotExist:
                    return Response(
                        {
                            "categoryId": [
                                "Category does not exist."
                            ]
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            name = request.data.get("name", obj.name).strip()

            if Artist.objects.filter(
                category=new_category,
                name__iexact=name,
            ).exclude(pk=obj.pk).exists():
                return Response(
                    {"name": ["This name already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj.name = name
            obj.category = new_category

            if "nationality" in request.data:
                obj.nationality = request.data["nationality"]

            if "status" in request.data:
                obj.is_active = (
                    request.data["status"].lower() == "active"
                )

            obj.save()

            return Response({
                "id": str(obj.id),
                "name": obj.name,
                "categoryId": str(obj.category_id),
                "categoryName": obj.category.name,
                "nationality": obj.nationality,
                "status": "Active" if obj.is_active else "Inactive",
            })

        return Response(
            {"detail": "Unknown master."},
            status=status.HTTP_404_NOT_FOUND,
        )