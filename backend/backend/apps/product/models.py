from django.db import models
import datetime
import re
from django.core import validators
from django.utils import timezone
from accounts.models import Address, User


class ProductBrand(models.Model):
    
    brand = models.CharField(max_length=500, blank=True)
    brand_desc = models.CharField(max_length=500, default="name of quality", null=True, blank=True)
    brand_image = models.FileField(upload_to='brand_images', null=True, blank=True)
    brand_max_discount = models.CharField(max_length=128, null=True, blank=True)
    brand_id_erp = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return self.brand
    

class ProductCategory(models.Model):
    
    product_category = models.CharField(max_length=500, default="Tiles",null=True, blank=True)
    product_category_desc = models.CharField(max_length=500, null=True, blank=True)
    Erp_category_id = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return self.product_category+" category_id "+str(self.id)
    

class ProductSubCategory(models.Model):
    
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='category', default=None, null=True, blank=True)
    product_sub_category = models.CharField(max_length=255, null=True, blank=True)
    product_subcategory_desc = models.CharField(max_length=500, null=True, blank=True)
    Erp_Subcategory_id = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.id)


class ProductSubCategoryType(models.Model):
    sub_category= models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE, related_name='subcategorytype_names', default=None, null=True, blank=True) 
    sub_cat_type = models.CharField(max_length=500, null=True, blank=True)
    sub_cat_type_desc = models.CharField(max_length=500, null=True, blank=True)
    Erp_SubcategoryType_id = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.sub_category)


class Tags(models.Model):
    
    tag =  models.CharField(max_length=500, default='', null=True, blank=True)
    tag_desc = models.CharField(max_length=500, default='', null=True, blank=True)

    def __str__(self):
        return self.tag
    
    def delete(self, *args, **kwargs):
        self.products.clear()
        super().delete(*args, **kwargs)


class HeaderScrollable(models.Model):

    header_image = models.FileField(upload_to='header_images', null=True, blank=True)
    header_image_URL = models.URLField(max_length=500, default='', null=True, blank=True)

    def __str__(self):
        return str(self.header_image)


class Product(models.Model):
    product_sub_cat = models.ForeignKey(ProductSubCategory, on_delete=models.CASCADE, related_name='subcategory_names', default=None, null=True, blank=True)
    subcategorytype_id = models.ForeignKey(ProductSubCategoryType, on_delete=models.CASCADE, related_name='subcategorytype_names', default=None, null=True, blank=True) 
    product_name = models.CharField(max_length=500, null=True, blank=True)
    product_desc = models.CharField(max_length=512, null=True, blank=True)
    product_code = models.IntegerField(default=0, null=True, blank=True)
    product_color = models.CharField(max_length=500, null=True, blank=True)
    product_weight = models.CharField(max_length=500, null=True, blank=True)
    product_design = models.CharField(max_length=500, null=True, blank=True)
    product_shape = models.CharField(max_length=500, null=True, blank=True)
    product_finish = models.CharField(max_length=500,null=True, blank=True)
    product_themes = models.CharField(max_length=500,null=True, blank=True)
    product_tags = models.ManyToManyField(Tags, blank=True, related_name='products')
    header_scrollable = models.ForeignKey(HeaderScrollable, on_delete=models.CASCADE, related_name='HeaderScrollable_images', default=None, null=True, blank=True)
    product_brand = models.ForeignKey(ProductBrand, on_delete=models.CASCADE, related_name='Productbrand_names', default=None, null=True, blank=True)
    related_products = models.JSONField(null=True, blank=True)
    product_showrooms = models.JSONField(null=True, blank=True)
    is_wishlisted = models.BooleanField(default=False, null=True, blank=True)
    variations = models.JSONField(null=True, blank=True)
    item_id = models.CharField(max_length=500, null=True, blank=True)
    sku_name = models.CharField(max_length=500,null=True, blank=True)
    hsn_code = models.CharField(max_length=500,null=True, blank=True)
    bar_code = models.CharField(max_length=500, null=True, blank=True)
    uom = models.CharField(max_length=500, null=True, blank=True)
    length_in_inches = models.CharField(max_length=500, null=True, blank=True)
    breadth_in_inches = models.CharField(max_length=500, null=True, blank=True)
    height_in_inches = models.CharField(max_length=500, null=True, blank=True)
    length_in_mm = models.CharField(max_length=500, null=True, blank=True)
    breadth_in_mm = models.CharField(max_length=500, null=True, blank=True)
    height_in_mm = models.CharField(max_length=500, null=True, blank=True)
    overall_size_in_inches = models.CharField(max_length=500, null=True, blank=True)
    overall_size_in_mm = models.CharField(max_length=500, null=True, blank=True)
    lead_time = models.CharField(max_length=500, null=True, blank=True)
    total_stock = models.CharField(max_length=500, null=True, blank=True)
    liqudation = models.CharField(max_length=500, null=True, blank=True)
    product_price_with_tax = models.FloatField(default=0, null=True, blank=True)
    product_max_discount_percent = models.FloatField(default=0, null=True, blank=True)
    product_tax = models.FloatField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.product_name


class ProductPrice(models.Model):
    
    Types = (
        ('1', 'By Piece'),
        ('2', 'By SquareFeet')
    )
    mrp = models.FloatField(default=0, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='Product_prices', default=None, null=True, blank=True)
    product_price_type = models.CharField(max_length=255, choices=Types, default="1", null=True, blank=True)
    product_price = models.FloatField(default=0, null=True, blank=True)
    is_revealed = models.BooleanField(default=False, null=True, blank=True)
    tax = models.FloatField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.product)


class ProductImages(models.Model):
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ProductImages', default=None, null=True, blank=True)
    product_image = models.FileField(upload_to='product_images', null=True, blank=True)
    is_main_image = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return str(self.product_image)


class ProductRating(models.Model):

    products = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ProductRating', default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='UserRating', default=None, null=True, blank=True)
    product_rating = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.product_rating)


class ProductReview(models.Model):
    
    products = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ProductReview', default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='UserReview', default=None, null=True, blank=True)
    product_reveiw = models.CharField(max_length=255, default="good product", null=True, blank=True)
    product_rating = models.IntegerField(default=0, null=True, blank=True)
    name = models.CharField(max_length=255, default="user", null=True, blank=True)

    def __str__(self):
        return self.product_reveiw


class ProductFeedback(models.Model):
    
    FeedBack = (
        ('O' , 'Oral'),
        ('W' , 'Written'),
        ('I' , 'Informal'),
        ('E' , 'Evaluate'),
        ('S' , 'Self-Assesment')        
    )
    
    productFeeds = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ProductFeedback', default=None, null=True, blank=True)
    users = models.ForeignKey(User, on_delete=models.CASCADE, related_name='UserFeedback', default=None, null=True, blank=True)
    feedbackType = models.CharField(max_length=255, choices=FeedBack, default="1", null=True, blank=True)
    feedback = models.TextField(default='', null=True, blank=True)

    def __str__(self):
        return self.feedback


class ShowRoom(models.Model):
    
    address1 = models.TextField(default='', null=True, blank=True)
    address2 = models.TextField(default='', null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.IntegerField(default=0, null=True, blank=True)
    lat = models.FloatField(default=0, null=True, blank=True)
    lng = models.FloatField(default=0, null=True, blank=True)

    def __str__(self):
        return self.city


class ProductCart(models.Model):
    
    productCart = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ProductCart', default=None, null=True, blank=True)
    user_cart = models.ForeignKey(User, on_delete=models.CASCADE, related_name='UserCart', default=None, null=True, blank=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    price = models.FloatField(default=0, null=True, blank=True)

    def __str__(self):
        return str(self.quantity)
    

class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='userwishlist', default=None, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='productwishlist', default=None, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product')
    
    def __str__(self):
        return str(self.id)
    
class UserOrderSummary(models.Model):
    order_status = (
        ('O' , 'Order placed'),
        ('S' , 'shipped'),
        ('D' , 'Delivered'),
        ('C' , 'Cancelled')        
    )
    order_number = models.CharField(max_length=128, null=True, blank=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='order_summaries', null=True, blank=True)
    total_amt = models.FloatField(default=0, null=True, blank=True)
    total_quantity = models.IntegerField(default=0, null=True, blank=True)
    order_status = models.CharField(max_length=255, choices=order_status, default="O", null=True, blank=True)
    ordered_date = models.DateField(auto_now=True, null=True, blank=True)
    delivered_date = models.DateField(blank=True, null=True)
    address = models.ForeignKey(Address, on_delete=models.CASCADE, related_name='order_summaries', null=True, blank=True)
    
    def __str__(self):
        return str(self.id)

class UserOrderDetail(models.Model):
    order_status = (
        ('O' , 'Order placed'),
        ('S' , 'shipped'),
        ('D' , 'Delivered'),
        ('C' , 'Cancelled')        
    )
    quantity = models.IntegerField(default=0, null=True, blank=True)
    price = models.FloatField(default=0, null=True, blank=True)
    order_summary = models.ForeignKey(UserOrderSummary, on_delete=models.CASCADE, related_name='order_details', null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_details', null=True, blank=True)
    product_status = models.CharField(max_length=255, choices=order_status, default="O", null=True, blank=True)
    delivered_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.id)
    
class Transaction(models.Model):
    mihpayid = models.CharField(max_length=512, blank=True, null=True , default=None)
    txnid = models.CharField(max_length=128, blank=True, null=True , default=None)
    addedon = models.DateTimeField(null=True,blank=True)
    hash = models.CharField(max_length=512, blank=True, null=True , default=None)
    bank_ref_num = models.CharField(max_length=256, blank=True, null=True , default=None)
    bankcode = models.CharField(max_length=256, blank=True, null=True , default=None)
    mode = models.CharField(max_length=128, blank=True, null=True , default=None)
    transaction_status = models.CharField(max_length=128, blank=True, null=True , default=None)
    key = models.CharField(max_length=128, blank=True, null=True , default=None)
    order_summary = models.ForeignKey(UserOrderSummary, on_delete=models.CASCADE, related_name='transaction', null=True, blank=True)

    def __str__(self):
        return str(self.id)
    
class Pincodes(models.Model):
    pincode_list =  models.JSONField()