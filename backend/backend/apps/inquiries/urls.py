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
    path("", InquiryListView.as_view(), name="inquiry-list"),
    path("counts/", InquiryCountsView.as_view(), name="inquiry-counts"),

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
        "masters/<str:kind>/options/",
        MasterOptionsView.as_view(),
        name="master-options",
    ),
    path(
        "masters/<str:kind>/<uuid:pk>/",
        MasterDetailView.as_view(),
        name="master-detail",
    ),
    path(
        "masters/<str:kind>/",
        MasterListView.as_view(),
        name="master-list",
    ),

    # ==================================================
    # Inquiry UUID routes
    # ==================================================
    path(
        "<uuid:pk>/activities/",
        InquiryActivityListView.as_view(),
        name="inquiry-activities",
    ),
    path(
        "<uuid:pk>/",
        InquiryDetailView.as_view(),
        name="inquiry-detail",
    ),
    path(
        "masters/<str:kind>/<uuid:pk>/",
        MasterDetailView.as_view(),
        name="master-detail",
    ),
]