from django.urls import path

from .views import AdminDashboardView, RMDashboardView

urlpatterns = [
    path("admin/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("rm/",RMDashboardView.as_view(),name="rm-dashboard",),
]