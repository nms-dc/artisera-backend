from django.shortcuts import render
from rest_framework import viewsets
from company.models import Company
from company.api.serializers import CompanySerializer

class CompanyView(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
