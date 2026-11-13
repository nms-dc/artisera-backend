from django.urls import path
from .views import (
    InquirySummaryView,
    InquiryDetailReportView,
    InquiryDetailExportView,
)

urlpatterns = [
    path(
        "inquiry-summary/",
        InquirySummaryView.as_view(),
        name="inquiry-summary",
    ),

    path(
        "inquiry-detail/export/",
        InquiryDetailExportView.as_view(),
        name="inquiry-detail-export",
    ),

    path(
        "inquiry-detail/",
        InquiryDetailReportView.as_view(),
        name="inquiry-detail-report",
    ),
]