from django.urls import URLPattern, path, include
from ERPintegration.api.views import ErpProductView, ErpUserView
from rest_framework.routers import DefaultRouter

app_name = "ERP"

router = DefaultRouter()
router.register('erp', ErpProductView)
router.register('user', ErpUserView)
urlpatterns = [
    path('', include(router.urls)),
]
