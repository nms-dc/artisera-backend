from django.db.models.signals import post_save
from django.dispatch import receiver
from company.models import Company

@receiver(post_save , sender = Company)
def company_post_save(sender , instance , *args ,**kwargs):
    if instance.is_verified is True:
        print("Congratulations!!!, company is verified")
    else:
        print("company is not verified yet! , finger crossed")
