from django.contrib import admin
from product.models  import Product, ProductBrand, ProductCart, ProductCategory, ProductFeedback, ProductImages, ProductPrice\
    , ProductRating, ProductReview, ProductSubCategory, HeaderScrollable, Transaction, UserOrderSummary, Tags, ShowRoom,Pincodes,ProductSubCategoryType\
    ,Address,UserOrderDetail
from import_export.admin import ExportActionMixin
from import_export.admin import ImportExportModelAdmin
# Register your models here.
# Register your models here.

class ProductsBrandAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('brand', 'brand_desc', "brand_id_erp")
    list_filter = ('brand', )
    fieldsets = (
        (None, {'fields': ('brand', 'brand_desc', 'brand_image', "brand_id_erp")}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('brand', 'brand_desc', 'brand_image', ),
        }),
    )
    search_fields = ('brand', )
    ordering = ('brand', )
    filter_horizontal = ()

class ProductsCategoryAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('product_category', 'product_category_desc', )
    list_filter = ('product_category', )
    fieldsets = (
        (None, {'fields': ('product_category', 'product_category_desc' )}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('product_category', 'product_category_desc',),
        }),
    )
    search_fields = ('product_category', )
    ordering = ('product_category', )
    filter_horizontal = ()

class ProductSubCategoryAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('product_category', 'product_sub_category', )
    list_filter = ('product_sub_category', )
    fieldsets = (
        (None, {'fields': ('product_category', 'product_sub_category', 'product_subcategory_desc',)}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('product_category', 'product_sub_category', 'product_subcategory_desc',  ),
        }),
    )
    search_fields = ('product_sub_category', )
    ordering = ('product_sub_category', )
    filter_horizontal = ()


class TagsAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('tag', 'tag_desc', )
    list_filter = ('tag', )
    fieldsets = (
        (None, {'fields': ('tag', 'tag_desc', )}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('tag', 'tag_desc', ),
        }),
    )
    search_fields = ('tag', )
    ordering = ('tag', )
    filter_horizontal = ()


class HeaderScrollableAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('header_image', 'header_image_URL', )
    list_filter = ('header_image', )
    fieldsets = (
        (None, {'fields': ('header_image', 'header_image_URL', )}),)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('header_image', 'header_image_URL', ),
        }),
    )
    search_fields = ('header_image', )
    ordering = ('header_image', )
    filter_horizontal = ()


class ProductAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('id','product_name', 'product_code', 'product_brand', 'product_sub_cat','product_sub_cat_product_category_product_category')
    list_filter = ('product_name', )

    def product_sub_cat_product_category_product_category(self, obj):
        if obj.product_sub_cat and obj.product_sub_cat.product_category:
            return obj.product_sub_cat.product_category.product_category
        return None
    
    product_sub_cat_product_category_product_category.short_description = 'Product category'
    readonly_fields = ('product_sub_cat_product_category_product_category',)
        
    fieldsets = (
        (None, {'fields': ('product_name', 'product_code', )}),
        ('product info',{'fields':('product_sub_cat_product_category_product_category','product_sub_cat', 'product_color', 'subcategorytype_id')}), 
        ('more info',{'fields': ('product_shape', 'product_finish', 'product_themes', 'header_scrollable', 'item_id',
                                 'sku_name','hsn_code','bar_code', 'uom', 'length_in_inches','breadth_in_inches',
                                 'length_in_mm', 'breadth_in_mm', 'overall_size_in_inches', 'overall_size_in_mm','lead_time'
                                 ,'total_stock', 'liqudation', 'is_wishlisted')}),
        ('showroom',{'fields': ('product_showrooms', 'related_products')})
        )
    class ProductTagInline(admin.TabularInline):  # or StackedInline
        model = Product.product_tags.through
    inlines = [ProductTagInline,]
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('product_name', 'product_code', 'product_brand', ),
        }),
    )
    search_fields = ('product_name', 'product_code')
    ordering = ('product_name', )
    filter_horizontal = ()


class ProductPriceAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('product', 'product_price_type', )
    list_filter = ('product', )
    fieldsets = (
        (None, {'fields': ('product', 'product_price_type', 'product_price', 'is_revealed', )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('product', 'product_price_type', ),
        }),
    )
    search_fields = ('product', )
    ordering = ('product', )
    filter_horizontal = ()


class ProductImagesAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('product', 'product_image', )
    list_filter = ('product', )
    fieldsets = (
        (None, {'fields': ('product', 'product_image', 'is_main_image', )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('product', 'product_image', ),
        }),
    )
    search_fields = ('product', )
    ordering = ('product', )
    filter_horizontal = ()


class ProductRatingAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('products', 'user', )
    list_filter = ('products', )
    fieldsets = (
        (None, {'fields': ('products', 'user', 'product_rating', )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('products', 'product_rating', ),
        }),
    )
    search_fields = ('products', )
    ordering = ('products', )
    filter_horizontal = ()


class ProductReviewAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('products', 'user', )
    list_filter = ('products', )
    fieldsets = (
        (None, {'fields': ('products', 'user', 'product_reveiw', )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('products', 'product_reveiw', ),
        }),
    )
    search_fields = ('products', )
    ordering = ('products', )
    filter_horizontal = ()


class ProductFeedbackAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('productFeeds', 'users', )
    list_filter = ('productFeeds', )
    fieldsets = (
        (None, {'fields': ('productFeeds', 'feedbackType', 'feedback', 'users' )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('productFeeds', 'feedbackType', ),
        }),
    )
    search_fields = ('productFeeds', )
    ordering = ('productFeeds', )
    filter_horizontal = ()


class ShowRoomAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('city', 'address1', )
    list_filter = ('city', )
    fieldsets = (
        (None, {'fields': ('city', 'address1', 'address2', 'state', 'zipcode', 'lat',  'lng')}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('ProductFeeds', 'FeedbackType', ),
        }),
    )
    search_fields = ('city', )
    ordering = ('city', )
    filter_horizontal = ()


class ProductCartAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('productCart', 'user_cart', )
    list_filter = ('productCart', )
    fieldsets = (
        (None, {'fields': ('user_cart', 'quantity', 'price', )}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('productCart', 'user_cart', ),
        }),
    )
    search_fields = ('productCart', )
    ordering = ('productCart', )
    filter_horizontal = ()

class UserOrderDetailInline(admin.TabularInline):
    model = UserOrderDetail
    extra = 0
    
class UserOrderSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_number', 'user_first_name', 'total_amt', 'total_quantity', )
    list_filter = ('user__id',)
    inlines = [UserOrderDetailInline]

    def user_first_name(self, obj):
        if obj.user:
            return obj.user.first_name
        else:
            return "No user"

    user_first_name.short_description = 'User First Name'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['order_number', 'user', 'total_amt', 'total_quantity', 'display_address']
        return []

    def display_address_id(self, obj):
        if obj.address:
            return obj.address.id
        else:
            return "No address available"

    display_address_id.short_description = 'Address ID'

    def display_address(self, obj):
        if obj.address:
            address = obj.address
            return f"{address.address_one}, {address.address_two}, {address.city}, {address.pincode}, {address.state}, {address.phone_no}"
        else:
            return "No address available"

    display_address.short_description = 'Shipping Address'

    fieldsets = [
        ('Order Information', {
            'fields': ('order_number', 'user', 'total_amt', 'total_quantity')
        }),
        ('Shipping Information', {
            'fields': ( 'display_address', 'address')
        }),
    ]


class pincodeAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('pincode_list', )


class SubcategoryTypeAdmin(ImportExportModelAdmin,admin.ModelAdmin):
    list_display = ('sub_category','sub_cat_type', 'sub_cat_type_desc', )
    list_filter = ('sub_cat_type', )
    fieldsets = (
        (None, {'fields': ('Erp_SubcategoryType_id', 'sub_cat_type_desc', 'sub_cat_type')}),
        )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('Erp_SubcategoryType_id', 'sub_cat_type_desc', ),
        }),
    )
    search_fields = ('sub_cat_type', )
    ordering = ('sub_cat_type', )
    filter_horizontal = ()


#registering model
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductBrand, ProductsBrandAdmin)
admin.site.register(ProductCart, ProductCartAdmin)
admin.site.register(ProductCategory, ProductsCategoryAdmin)
admin.site.register(ProductFeedback, ProductFeedbackAdmin)
admin.site.register(ProductImages, ProductImagesAdmin)
admin.site.register(ProductPrice, ProductPriceAdmin)
admin.site.register(ProductRating, ProductRatingAdmin)
admin.site.register(ProductReview, ProductReviewAdmin)
admin.site.register(ProductSubCategory, ProductSubCategoryAdmin)
admin.site.register(HeaderScrollable, HeaderScrollableAdmin)
admin.site.register(UserOrderSummary, UserOrderSummaryAdmin)
admin.site.register(Tags, TagsAdmin)
admin.site.register(ShowRoom, ShowRoomAdmin)
admin.site.register(Pincodes, pincodeAdmin)
admin.site.register(ProductSubCategoryType, SubcategoryTypeAdmin)
admin.site.register(Address)
admin.site.register(Transaction)


