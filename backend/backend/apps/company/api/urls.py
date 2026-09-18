from django.urls import URLPattern, path, include, re_path
from rest_framework.routers import DefaultRouter
from company.api.views import CompanyView


app_name = "company"

router = DefaultRouter()
router.register('company-regist', CompanyView)


urlpatterns = [
     path('', include(router.urls)),
]