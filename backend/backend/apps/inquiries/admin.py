from django.contrib import admin
from .models import Customer, Category, Subcategory, Artist, Inquiry


admin.site.register(Customer)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Artist)
admin.site.register(Inquiry)