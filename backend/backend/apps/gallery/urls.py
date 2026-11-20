from django.urls import path

from .views import (
    GalleryDashboardView,
    GalleryCustomerOptionsView,
    GallerySaleListView,
    GallerySaleExportView,
    GallerySaleProductView,
)

urlpatterns = [
    path("dashboard/", GalleryDashboardView.as_view(), name="gallery-dashboard"),
    path(
        "customers/",
        GalleryCustomerOptionsView.as_view(),
        name="gallery-customers",
    ),
    path("sales/", GallerySaleListView.as_view(), name="gallery-sales"),
    path("sales/export/", GallerySaleExportView.as_view(), name="gallery-sales-export"),
    path(
        "sales/<uuid:pk>/products/<uuid:product_id>/",
        GallerySaleProductView.as_view(),
        name="gallery-sale-product",
    ),
]
