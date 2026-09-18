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


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/account/', include('accounts.api.urls', 'accounts_api')),
    path('api/v1/product/', include('product.api.urls', 'product_api')),
    path('api/v1/company/', include('company.api.urls', 'company_api')),
    path('auth/',include('drf_social_oauth2.urls',namespace='drf')),
    path('schema', SpectacularAPIView.as_view(), name = 'api-schema'),
    path('docs', SpectacularSwaggerView.as_view(url_name = 'api-schema'),name = 'api-docs')    
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)