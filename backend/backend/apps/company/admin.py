# from django.contrib import admin

# # Register your models here.
# from django.contrib import admin
# from company.models import Company
# from import_export.admin import ExportActionMixin
# from import_export.admin import ImportExportModelAdmin
# # Register your models here.
# # Register your models here.

# class CompanyAdmin(ImportExportModelAdmin,admin.ModelAdmin):
#     list_display = ('company_name', 'phone', 'email' ,'contact_first_name' , 'contact_last_name' , 'is_verified')
#     list_filter = ('company_name', )
#     fieldsets = (
#         (None, {'fields': ('company_name', 'gst_code')}),
#         ('Company info',{'fields':('pan_no' ,'description','contact_first_name','contact_last_name')}),
#         ('Contact info',{'fields':('phone','email',)}),
#         ('Address info',{'fields':('address_one','address_two','pincode','city')}),
#         ('Authentication',{'fields':('is_verified',)})
#         )
#     search_fields = ('company_name', )
#     ordering = ('company_name', )
#     filter_horizontal = ()


# #registering model
# admin.site.register(Company, CompanyAdmin)



