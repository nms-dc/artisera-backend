from django.urls import path

from .views import (
    InquiryListView,
    InquiryCountsView,
    InquiryDetailView,
    InquiryActivityListView,
    CustomerListView,
    CustomerLocationsView,
    CustomerDetailView,
    CustomerActivitiesView,
    MasterOptionsView,
    MasterListView,
    MasterDetailView,
    InquiryAssignView,
    InquiryBulkView,
    InquiryStatusView,
    InquiryWonView,
    CustomerSalesView,
    InquiryTouchbaseView,
)

urlpatterns = [
    # ==================================================
    # Inquiries - fixed paths
    # ==================================================
    path("crm/inquiries/", InquiryListView.as_view(), name="inquiry-list"),
    path("crm/inquiries/counts/", InquiryCountsView.as_view(), name="inquiry-counts"),
    # ==================================================
    # Customers
    # ==================================================
    path(
        "crm/customers/locations/",
        CustomerLocationsView.as_view(),
        name="customer-locations",
    ),
    path(
        "crm/customers/",
        CustomerListView.as_view(),
        name="customer-list",
    ),
    path(
        "crm/customers/<uuid:pk>/activities/",
        CustomerActivitiesView.as_view(),
        name="customer-activities",
    ),
    path(
        "crm/customers/<uuid:pk>/",
        CustomerDetailView.as_view(),
        name="customer-detail",
    ),
    # ==================================================
    # Masters
    # ==================================================
    path(
        "common/<str:kind>/options/",
        MasterOptionsView.as_view(),
        name="master-options",
    ),
    path(
        "common/<str:kind>/<uuid:pk>/",
        MasterDetailView.as_view(),
        name="master-detail",
    ),
    path(
        "common/<str:kind>/",
        MasterListView.as_view(),
        name="master-list",
    ),
    # ==================================================
    # Inquiry UUID routes
    # ==================================================
    path(
        "crm/inquiries/<uuid:pk>/activities/",
        InquiryActivityListView.as_view(),
        name="inquiry-activities",
    ),
    path(
        "crm/inquiries/<uuid:pk>/",
        InquiryDetailView.as_view(),
        name="inquiry-detail",
    ),
    path(
        "masters/<str:kind>/<uuid:pk>/",
        MasterDetailView.as_view(),
        name="master-detail",
    ),
    path(
        "crm/inquiries/<uuid:pk>/assign/",
        InquiryAssignView.as_view(),
        name="inquiry-assign",
    ),
    path(
        "crm/inquiries/bulk/",
        InquiryBulkView.as_view(),
        name="inquiry-bulk",
    ),
    path(
        "crm/inquiries/<uuid:pk>/status/",
        InquiryStatusView.as_view(),
        name="inquiry-status",
    ),
    path(
        "crm/inquiries/<uuid:pk>/won/",
        InquiryWonView.as_view(),
        name="inquiry-won",
    ),
    path(
        "crm/customers/<uuid:pk>/sales/",
        CustomerSalesView.as_view(),
        name="customer-sales",
    ),
    path(
        "crm/inquiries/<uuid:pk>/touchbase/",
        InquiryTouchbaseView.as_view(),
        name="inquiry-touchbase",
    ),
]
