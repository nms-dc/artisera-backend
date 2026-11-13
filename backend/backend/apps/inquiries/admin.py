from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import Customer, Category, Subcategory, Artist, Inquiry


@admin.register(Customer)
class CustomerAdmin(ImportExportModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    pass


@admin.register(Subcategory)
class SubcategoryAdmin(ImportExportModelAdmin):
    pass


@admin.register(Artist)
class ArtistAdmin(ImportExportModelAdmin):
    pass


@admin.register(Inquiry)
class InquiryAdmin(ImportExportModelAdmin):
    pass
