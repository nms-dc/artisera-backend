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
        "customers/locations/",
        CustomerLocationsView.as_view(),
        name="customer-locations",
    ),
    path(
        "customers/",
        CustomerListView.as_view(),
        name="customer-list",
    ),
    path(
        "customers/<uuid:pk>/activities/",
        CustomerActivitiesView.as_view(),
        name="customer-activities",
    ),
    path(
        "customers/<uuid:pk>/",
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
]
