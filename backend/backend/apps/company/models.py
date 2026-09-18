from django.db import models

# Create your models here.

class Company(models.Model): 
    company_name = models.CharField(max_length=200,  blank=True)
    gst_code = models.CharField(max_length=200, default=None, null=True,  blank=True)
    pan_no = models.CharField(max_length=200, default=None, null=True,  blank=True)
    description = models.TextField(default=None, null=True,  blank=True)
    phone = models.CharField(max_length=200, default=None, null=True)
    email = models.EmailField(default=None, null=True)
    address_one = models.TextField(default=None, null=True,  blank=True)
    address_two = models.TextField(default=None, null=True,  blank=True)
    pincode = models.IntegerField(default=None, null=True,  blank=True)
    city = models.CharField(max_length=200, default=None, null=True,  blank=True)
    contact_first_name = models.CharField(max_length=200, default=None, null=True,  blank=True)
    contact_last_name = models.CharField(max_length=200, default=None, null=True,  blank=True)
    is_verified = models.BooleanField(default=False)
    

    def __str__(self):
        return self.company_name
    
    class Meta:
        verbose_name_plural = "Company"    


# from django.db.models.signals import post_save
# from django.dispatch import receiver

# @receiver(post_save , sender = Company)
# def company_post_save(sender , instance , *args ,**kwargs):
#     if instance.is_verified is True:
#         print(instance.company_name ,"is verified is true, so company is verified")
#     else:
#         print(instance.company_name ,"company is not verified yet")