from django.db.models.signals import post_save
from django.dispatch import receiver
from product.models import Product


@receiver(post_save, sender=Product)
def copy_measurements(sender, instance, created, *args, **kwargs):
    print('hello world from cycle siganls')
    #if instance:

