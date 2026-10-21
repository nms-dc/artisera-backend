from django.urls import path
from common.views import  create_inquiry ,TriggerTaskView
app_name = 'company_api'

urlpatterns = [
    path('trigger-task/', TriggerTaskView.as_view(), name='trigger-task'),
    path("inquiries/",create_inquiry),
]
