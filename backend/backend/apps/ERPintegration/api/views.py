from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
import copy
from rest_framework.response import Response
from rest_framework import viewsets
from ERPintegration.api.serializers import ErpProductSerailzier, ErpUserSerailzier
from ERPintegration.models import ProductInErp, ERPUser
from rest_framework.pagination import PageNumberPagination


# class StandardResultsSetPagination(PageNumberPagination):
#     page_size = 5
#     page_size_query_param = 'page_size'
#     max_page_size = 1000

class ErpProductView(viewsets.ModelViewSet):
    serializer_class = ErpProductSerailzier
    queryset = ProductInErp.objects.all()
    #pagination_class = StandardResultsSetPagination
    


class ErpUserView(viewsets.ModelViewSet):
    queryset = ERPUser.objects.all()
    serializer_class = ErpUserSerailzier