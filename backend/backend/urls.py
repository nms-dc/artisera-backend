"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from  django.conf import settings
from django.contrib.auth.views import LogoutView
from django.views.generic import TemplateView
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/account/', include('accounts.api.urls', 'accounts_api')),
    path('api/v1/product/', include('product.api.urls', 'product_api')),
    #path('api/v1/company/', include('company.api.urls', 'company_api')),
    path('api/v1/common/', include('common.urls', 'company_api')),
    #path('auth/',include('drf_social_oauth2.urls',namespace='drf')),
    path('schema', SpectacularAPIView.as_view(), name = 'api-schema'),
    path('docs', SpectacularSwaggerView.as_view(url_name = 'api-schema'),name = 'api-docs'),   
    # new login for artisera
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("dashboard/", include("dashboard.urls")),
    path("api/v1/inquiries/", include("inquiries.urls")),
    path("reports/", include("reports.urls")),
    path("notifications/",include("notifications.urls"),),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)