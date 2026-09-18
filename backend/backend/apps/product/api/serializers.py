
from django.utils import timezone
from rest_framework import serializers
from product.models import Product, ProductBrand, ProductCart, ProductCategory, ProductFeedback, ProductImages,\
    ProductPrice, ProductRating, ProductReview, ProductSubCategory, ShowRoom, HeaderScrollable, Tags, \
      ProductSubCategoryType, Pincodes, Address, Transaction , UserOrderDetail,UserOrderSummary, WishlistItem
from accounts.models import User
from accounts.api.serializers import UserProfileInfoSerializer
from django.core.mail import send_mail
import json
import pandas as pd

class TagsSerializer(serializers.ModelSerializer):

   class Meta:
      model = Tags
      fields = '__all__'

class ProductBrandSerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductBrand
      fields = '__all__'


class ProductCategorySerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductCategory
      fields = '__all__'

class ProductSubCategorySerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductSubCategory
      fields = '__all__'


class SubCategoryListSerializers(serializers.ModelSerializer):
   subcat_list = serializers.SerializerMethodField()

   def get_subcat_list(self,obj):
      data = ProductSubCategory.objects.filter(product_category = obj.id)
      serialize = ProductSubCategorySerializers(data, many=True).data
      return serialize

   class Meta:
      model = ProductSubCategory
      fields = ['subcat_list']


class ProductSubCategoryTypeSerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductSubCategoryType
      fields = '__all__'

   def create(self, validated_data):
      subcategory_datas = ProductSubCategory.objects.all()
      serialized_subcats = ProductSubCategorySerializers(subcategory_datas, many=True).data
      subcategory_ids={}
      #storing all the category ids into dictionary to filter subcategorys
      for subcat_dictionary in serialized_subcats:
         #if the same key the data will get override
         subcategory_ids[subcat_dictionary["Erp_Subcategory_id"]]=subcat_dictionary["id"]

      subcategory_datas = open("backend/apps/product/api/categorys.json")
      subcategorytype_data = json.load(subcategory_datas)
      print(subcategory_ids)

      for subcategorytype in subcategorytype_data['data']['category']:

         if subcategorytype['main_model']=="subcattype":
            print(subcategorytype)

            if int(subcategorytype['main_parent']) in subcategory_ids.keys():
               subcategory_id = subcategory_ids[int(subcategorytype['main_parent'])]
               print(type(subcategory_id))
               subcategorytype_instance = ProductSubCategoryType.objects.create(
                  #product_category = category_id,
                  sub_cat_type = subcategorytype['name'],
                  sub_cat_type_desc = subcategorytype["description"]+"foreign key of category"+str(subcategory_id),
                  Erp_SubcategoryType_id = subcategorytype["catid"]
               )
      return subcategorytype_instance

# class CategoryMenuSerializers(serializers.ModelSerializer):
#    subcat_list = serializers.SerializerMethodField()

#    def get_subcat_list(self,obj):
#       data = ProductCategory.objects.all()
#       serialize = ProductCategorySerializers(data, many=True).data
#       datas = []
#       count = 1
#       for i in serialize:
#          id = i['id']
#          data = ProductSubCategory.objects.filter(product_category = id)
#          serializes = ProductSubCategorySerializers(data, many=True).data
#          datas.append(serializes)
#       #print(datas)
#       for data,nested in zip(datas, serialize):
#          id = nested['id']
#          if id == data[0]['product_category']:
#             nested['subcategorys'] = data
#             nests = nested['subcategorys']

#       print('serialize',serialize)
#       # for subcat in serialize:
#       #    print(subcat)
#       #    break
#          # subtype = subcat['subcategorys']
#          # for type in subtype:
#          #    print(type['id'], end=',')



#       return serialize

#    class Meta:
#       model = Tags
#       fields = '__all__'

class HeaderScrollableSerializers(serializers.ModelSerializer):

   class Meta:
      model = HeaderScrollable
      fields = '__all__'


class ImageSerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductImages
      fields = '__all__'


class TypeFilterSerializers(serializers.ModelSerializer):
   types = serializers.SerializerMethodField()

   def get_types(self,obj):
      data = ProductSubCategoryType.objects.filter(sub_category = obj.id)
      serialize = ProductSubCategoryTypeSerializers(data, many=True).data
      return serialize

   class Meta:
      model = ProductSubCategoryType
      fields = ['types']


class BasicSerializers(serializers.ModelSerializer):

   class Meta:
      model = Product
      fields = '__all__'

class BasicPriceSerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductPrice
      fields = '__all__'

class ProductSerializerListDisplay(serializers.ModelSerializer):
   image = serializers.SerializerMethodField()
   product_cat = serializers.SerializerMethodField()
   brand = serializers.SerializerMethodField()
   product_sub_category = serializers.SerializerMethodField()

   def to_representation(self, instance):
        data = super().to_representation(instance)
        tags_data = Tags.objects.filter(id__in=data['product_tags']).values('id', 'tag', 'tag_desc')
        data['product_tags'] = tags_data
        return data

   def get_image(self, obj):
      data = ProductImages.objects.filter(product= obj.id)
      serialize = ImageSerializers(data, many=True).data
      return serialize

   def get_product_cat(self, obj):
      data = ProductSubCategory.objects.filter(id=obj.product_sub_cat_id).values()
      name='no product category exists'
      if data:
         cat_id=data[0]['product_category_id']
         pro_data = ProductCategory.objects.filter(id = cat_id).values()
         name=pro_data[0]['product_category']
      return name


   def get_brand(self, obj):
      if obj.product_brand:
         return obj.product_brand.brand
      return None

   def get_product_sub_category(self, obj):
      if obj.product_sub_cat:
         return obj.product_sub_cat.product_sub_category
      return None


   class Meta:
         model = Product
         fields = ('id', 'product_name', 'product_price_with_tax', 'product_code','sku_name', 'product_color', 'product_code', 'image', 'product_cat', 'brand', 'product_sub_category', 'product_tags')



class ProductSerializers(serializers.ModelSerializer):
   # related_product_details = serializers.SerializerMethodField()
   # price = serializers.SerializerMethodField()
   image = serializers.SerializerMethodField()
   review = serializers.SerializerMethodField()
   product_cat = serializers.SerializerMethodField()
   product_cat_id = serializers.SerializerMethodField()
   brand = serializers.SerializerMethodField()
   product_sub_category = serializers.SerializerMethodField()

   def get_review(self, obj):
      try:
         review_data = ProductReview.objects.filter(products = obj.id)
         serialize = ProductReviewSerializers(review_data, many=True).data
         return serialize
      except:
         pass



   # def get_price(self, obj):
   #    try:
   #       data = ProductPrice.objects.filter(product = obj.id)
   #       serialize = BasicPriceSerializers(data, many=True).data
   #       if serialize:
   #          #print('price_details',serialize[0]['product_price'])
   #          return serialize[0]['product_price']
   #    except:
   #       pass

   # def get_related_product_details(self,obj):
   #    try:
   #       product_data = Product.objects.filter(id = obj.id)
   #       product_serialize_data = BasicSerializers(product_data, many=True).data
   #       data=[]
   #       for related in product_serialize_data:
   #          related_id = related['related_products']
   #          if type(related_id) == str:
   #             extracted_id = related_id.replace('{', '').replace('}', '').replace(" ", "").replace("'","").replace(":",'').replace("related", '').replace('"','').replace('[','').replace(']','').split(',')
   #             for id in extracted_id:
   #                if id != "" and id != 0:
   #                   related_product_data = Product.objects.filter(id = int(id))
   #                   related_serialize_data = BasicSerializers(related_product_data, many=True).data
   #                   print(related_serialize_data)
   #                   if related_serialize_data:
   #                      prod_id = related_serialize_data[0]['id']
   #                      #print(prod_id)
   #                      image_data = ProductImages.objects.filter(product = prod_id)
   #                      image_serialize = ProductImagesSerializers(image_data, many=True).data
   #                      #print(image_serialize)
   #                      related_serialize_data[0]['image_details'] = image_serialize
   #                      data.append(related_serialize_data[0])
   #       return data
   #    except:
   #       pass

   # def get_product_tags(self, obj):
   #    # Serialize the product_tags field as a list of tag IDs
   #    return [tag.id for tag in obj.product_tags.all()]

   def to_representation(self, instance):
        data = super().to_representation(instance)
        tags_data = Tags.objects.filter(id__in=data['product_tags']).values('id', 'tag', 'tag_desc')
        data['product_tags'] = tags_data
        return data

   def get_image(self, obj):
      data = ProductImages.objects.filter(product= obj.id)
      serialize = ImageSerializers(data, many=True).data
      return serialize

   def get_product_cat(self, obj):
      data = ProductSubCategory.objects.filter(id=obj.product_sub_cat_id).values()
      name='no product category exists'
      if data:
         cat_id=data[0]['product_category_id']
         pro_data = ProductCategory.objects.filter(id = cat_id).values()
         name=pro_data[0]['product_category']
      return name

   def get_product_cat_id(self, obj):
      data = ProductSubCategory.objects.filter(id=obj.product_sub_cat_id).values()
      name='no product category exists'
      if data:
         name=data[0]['product_category_id']

      return name

   def get_brand(self, obj):
      if obj.product_brand:
         return obj.product_brand.brand
      return None

   def get_product_sub_category(self, obj):
      if obj.product_sub_cat:
         return obj.product_sub_cat.product_sub_category
      return None

   class Meta:
      model = Product
      fields = '__all__'

   def create(self,validated_data):
      tag_ids = validated_data.pop('product_tags', [])
      product_instance = Product.objects.create(
                           product_sub_cat_id = validated_data.get('subcat_id'),
                           subcategorytype_id = validated_data.get('subcategorytype_id'),
                           product_name = validated_data.get('product_name'),
                           product_desc = validated_data.get('product_desc'),
                           product_code = validated_data.get('product_code'),
                           product_color = validated_data.get('product_color'),
                           product_design = validated_data.get('product_design'),
                           product_weight = validated_data.get('product_weight'),
                           product_shape = validated_data.get('product_shape'),
                           product_finish = validated_data.get('product_finish'),
                           product_themes = validated_data.get('product_themes'),
                           header_scrollable = validated_data.get('header_scrollable'),
                           product_brand = validated_data.get('product_brand'),
                           related_products = validated_data.get('related_products'),
                           product_showrooms = validated_data.get('product_showrooms'),
                           is_wishlisted = validated_data.get('is_wishlisted'),
                           variations = validated_data.get('variations'),
                           item_id = validated_data.get('item_id'),
                           sku_name = validated_data.get('sku_name'),
                           hsn_code = validated_data.get('hsn_code'),
                           bar_code = validated_data.get('bar_code'),
                           uom = validated_data.get('uom'),
                           length_in_inches = validated_data.get('length_in_inches'),
                           breadth_in_inches = validated_data.get('breadth_in_inches'),
                           height_in_inches = validated_data.get('height_in_inches'),
                           length_in_mm = validated_data.get('length_in_mm'),
                           breadth_in_mm = validated_data.get('breadth_in_mm'),
                           height_in_mm= validated_data.get('height_in_mm'),
                           overall_size_in_inches = validated_data.get('overall_size_in_inches'),
                           overall_size_in_mm = validated_data.get('overall_size_in_mm'),
                           lead_time = validated_data.get('lead_time'),
                           total_stock = validated_data.get('total_stock'),
                           liqudation = validated_data.get('liqudation'),
                           product_price_with_tax = validated_data.get('product_price_with_tax'),
                           product_max_discount_percent = validated_data.get('product_max_discount_percent'),
                           product_tax = validated_data.get('product_tax'),
                           created_at = timezone.now()
                        )
      product_instance.product_tags.set(tag_ids)
      return   product_instance

   def update(self, instance, validated_data):
      image_datas = self.context.get('view').request.FILES
      data = self.context['request'].data.get('product_image_id', None)
      '''#filtering 'pond_image_id' and converting it into an integer list'''
      int_Pimage_id = []
      if data:
         trim_image_id = data.replace('[', '').replace(']', '').replace(" ", "").split(',')
         for id in trim_image_id:
               int_Pimage_id.append(int(id))

      instance.product_sub_cat = validated_data.get('product_sub_cat', instance.product_sub_cat)
      instance.subcategorytype_id = validated_data.get('subcategorytype_id', instance.subcategorytype_id)
      instance.product_name = validated_data.get('product_name', instance.product_name)
      instance.product_code = validated_data.get('product_code', instance.product_code)
      instance.product_color = validated_data.get('product_color', instance.product_color)
      instance.product_desc = validated_data.get('product_desc', instance.product_desc)
      instance.product_shape = validated_data.get('product_shape', instance.product_shape)
      instance.product_finish = validated_data.get('product_finish', instance.product_finish)
      instance.product_themes = validated_data.get('product_themes', instance.product_themes)
      instance.product_design = validated_data.get('product_design', instance.product_design)
      instance.product_weight = validated_data.get('product_weight', instance.product_weight)
      instance.product_tags.set(validated_data.get('product_tags', instance.product_tags.all()))
      instance.header_scrollable = validated_data.get('header_scrollable', instance.header_scrollable)
      instance.product_brand = validated_data.get('product_brand', instance.product_brand)
      instance.related_products = validated_data.get('related_products', instance.related_products)
      instance.product_showrooms = validated_data.get('product_showrooms', instance.product_showrooms)
      instance.is_wishlisted = validated_data.get('is_wishlisted', instance.is_wishlisted)
      instance.variations = validated_data.get('variations', instance.variations)
      instance.item_id = validated_data.get('item_id', instance.item_id)
      instance.sku_name = validated_data.get('sku_name', instance.sku_name)
      instance.hsn_code = validated_data.get('hsn_code', instance.hsn_code)
      instance.bar_code = validated_data.get('bar_code', instance.bar_code)
      instance.uom = validated_data.get('uom', instance.uom)
      instance.length_in_inches = validated_data.get('length_in_inches', instance.length_in_inches)
      instance.breadth_in_inches = validated_data.get('breadth_in_inches', instance.breadth_in_inches)
      instance.height_in_inches = validated_data.get('height_in_inches', instance.height_in_inches)
      instance.length_in_mm = validated_data.get('length_in_mm', instance.length_in_mm)
      instance.breadth_in_mm = validated_data.get('breadth_in_mm', instance.breadth_in_mm)
      instance.height_in_mm = validated_data.get('height_in_mm', instance.height_in_mm)
      instance.overall_size_in_inches = validated_data.get('overall_size_in_inches', instance.overall_size_in_inches)
      instance.overall_size_in_mm = validated_data.get('overall_size_in_mm', instance.overall_size_in_mm)
      instance.lead_time = validated_data.get('lead_time', instance.lead_time)
      instance.total_stock = validated_data.get('total_stock', instance.total_stock)
      instance.liqudation = validated_data.get('liqudation', instance.liqudation)
      instance.product_price_with_tax = validated_data.get('product_price_with_tax', instance.product_price_with_tax)
      instance.product_max_discount_percent = validated_data.get('product_max_discount_percent', instance.product_max_discount_percent)
      instance.product_tax = validated_data.get('product_tax', instance.product_tax)
      instance.updated_at = timezone.now()

      instance.save()
      productimage_with_same_profile_instance = ProductImages.objects.filter(product=instance.pk).values_list('id', flat=True)

      if len(int_Pimage_id) != 0:
         for delete_id in productimage_with_same_profile_instance:
               if delete_id in int_Pimage_id:
                  ProductImages.objects.filter(pk=delete_id).delete()
      if len(image_datas.getlist('product_images')) != 0:
         for image_data in image_datas.getlist('product_images'):
               name = image_data.name
               ProductImages.objects.create(product=instance, product_image=image_data)

      return instance


class ProductPriceSerializers(serializers.ModelSerializer):

   # products = serializers.SerializerMethodField()

   # def get_products(self,  obj):

   #    data = Product.objects.filter(Product_prices = obj.id)
   #    serialize = ProductSerializers(data, many=True).data
   #    #print(data)
   #    return serialize

   class Meta:
      model = ProductPrice
      fields = '__all__'


class ProductImagesSerializers(serializers.ModelSerializer):

   class Meta:
      model = ProductImages
      fields = '__all__'


class ProductRatingSerializers(serializers.ModelSerializer):

   product = serializers.SerializerMethodField()
   user = serializers.SerializerMethodField()

   def get_product(self,  obj):

      data = Product.objects.filter(ProductRating = obj.id)
      serialize = ProductSerializers(data, many=True).data
      print(data)
      return serialize

   def get_user(self,  obj):

      data = User.objects.filter(UserRating = obj.id)
      serialize = UserProfileInfoSerializer(data, many=True).data
      print(data)
      return serialize

   class Meta:
      model = ProductRating
      fields = '__all__'


class ProductReviewSerializers(serializers.ModelSerializer):

   # product = serializers.SerializerMethodField()
   users = serializers.SerializerMethodField()

   def get_product(self,  obj):

      data = Product.objects.filter(ProductReview = obj.id)
      serialize = ProductSerializers(data, many=True).data
      print(serialize)
      return serialize

   def get_users(self,  obj):

      data = User.objects.filter(UserReview = obj.id)
      serialize = UserProfileInfoSerializer(data, many=True).data
      print(serialize)
      return serialize

   class Meta:
      model = ProductReview
      fields = '__all__'



class ProductFeedbackSerializers(serializers.ModelSerializer):

   product = serializers.SerializerMethodField()
   user = serializers.SerializerMethodField()

   def get_product(self,  obj):

      data = Product.objects.filter(ProductFeedback = obj.id)
      serialize = ProductSerializers(data, many=True).data
      print(data)
      return serialize

   def get_user(self,  obj):

      data = User.objects.filter(UserFeedback = obj.id)
      serialize = UserProfileInfoSerializer(data, many=True).data
      print(data)
      return serialize

   class Meta:
      model = ProductFeedback
      fields = '__all__'


class ProductCartSerializers(serializers.ModelSerializer):

   product = serializers.SerializerMethodField()
   user = serializers.SerializerMethodField()

   def get_product(self,  obj):

      data = Product.objects.filter(ProductCart = obj.id)
      serialize = ProductSerializers(data, many=True).data
      return serialize

   def get_user(self,  obj):

      data = User.objects.filter(UserCart = obj.id)
      serialize = UserProfileInfoSerializer(data, many=True).data
      return serialize

   class Meta:
      model = ProductCart
      fields = '__all__'


class ProductWishlistSerializer(serializers.ModelSerializer):
    product = ProductSerializers()
    user = UserProfileInfoSerializer()

    class Meta:
        model = WishlistItem
        fields = ('id','user', 'product')



class AddressSerializers(serializers.ModelSerializer):

   class Meta:
      model = Address
      fields = '__all__'

# class UserOrdersSerializers(serializers.ModelSerializer):
#    shipping_address = serializers.SerializerMethodField()
#    productId = serializers.SerializerMethodField()
#    customerId = serializers.SerializerMethodField()

   def get_productId(self,  obj):

      data = Product.objects.filter(ProductOrders = obj)
      serialize = ProductSerializers(data, many=True).data
      print(serialize[0]['id'])
      return serialize[0]['id']

   def get_customerId(self,  obj):

      data = User.objects.filter(Userorders = obj)
      serialize = UserProfileInfoSerializer(data, many=True).data
      print(serialize[0]['id'])
      return serialize[0]['id']

   def get_shipping_address(self, obj):

      data= Address.objects.filter(shipping_address = obj.id)
      serialize = AddressSerializer(data, many=True).data
      if serialize != []:
         print(serialize[0]['service_area'])
         result = {'street':serialize[0]['service_area'], 'city':serialize[0]['city'], 'state':serialize[0]['country'],
                  'zip_code':serialize[0]['pincode'],'country':serialize[0]['country']}
      else:
         result = {'address':'address not found'}
      return result
   class Meta:
      model = UserOrderSummary
      fields = '__all__'

   def create(self,validated_data):
      image_data = self.context.get('view').request.data
      order_instance = UserOrderSummary.objects.create(
         product_id = validated_data['product_id'],
         customer_id = validated_data['customer_id'],
         quantity = validated_data['quantity'],
         price = validated_data['price'],
         order_no = validated_data['order_no'],
         name = validated_data['name'],
         order_status = validated_data['status'],
      )
      address_data = image_data['shipping_address']
      address = eval(address_data)
      print(type(address))
      Address.objects.create(
         first_name = address['first_name'],
         last_name = address['last_name'],
         country = address['country'],
         pincode = address['pincode'],
         city = address['city'],
         phone_no = address['phone_no'],
         email_address = address['email_address'],
         service_area = address['street'],
         user_id = address['user'],
         shipping_address = order_instance,
      )


      return order_instance

   def update(self, instance, validated_data):
      image_datas = self.context.get('view').request.data
      instance.product_id = validated_data.get('product_id', instance.product_id)
      instance.customer_id = validated_data.get('customer_id', instance.customer_id)
      instance.quantity = validated_data.get('quantity', instance.quantity)
      instance.price = validated_data.get('price', instance.price)
      instance.order_no = validated_data.get('order_no', instance.order_no)
      instance.name = validated_data.get('name', instance.name)
      instance.status = validated_data.get('status', instance.status)
      instance.ordered_date = validated_data.get('ordered_date', instance.ordered_date)
      instance.delivered_date = validated_data.get('delivered_date', instance.delivered_date)
      instance.save()

      existing_shipping_address_with_same_profile_instance = Address.objects.filter(shipping_address=instance.pk).values_list('id', flat=True)
      print(existing_shipping_address_with_same_profile_instance)

      if existing_shipping_address_with_same_profile_instance:
         for delete_id in existing_shipping_address_with_same_profile_instance:
            Address.objects.filter(id=delete_id).delete()

      address_data = image_datas['shipping_address']
      address = eval(address_data)
      print(type(address))
      Address.objects.create(
         first_name = address['first_name'],
         last_name = address['last_name'],
         country = address['country'],
         pincode = address['pincode'],
         city = address['city'],
         phone_no = address['phone_no'],
         email_address = address['email_address'],
         service_area = address['street'],
         user_id = address['user'],
         shipping_address = instance,
      )

      return instance



class ShowRoomSerializers(serializers.ModelSerializer):

   class Meta:
      model = ShowRoom
      fields = '__all__'


class ByBrandSerializers(serializers.ModelSerializer):
   products = serializers.SerializerMethodField()

   def get_products(self, obj):
      data = Product.objects.all()
      serialize = ProductSerializers(data, many=True).data
      result = []
      for i in serialize:
         brand_id =i['subcat'][0]['category'][0]['brand'][0]['id']
         if obj.id == brand_id:
            result.append(i)
      return result

   class Meta:
      model = ProductBrand
      fields = ['products']



class ProductSearchSerializers(serializers.ModelSerializer):
   image = serializers.SerializerMethodField()
   price = serializers.SerializerMethodField()
   review = serializers.SerializerMethodField()

   def get_review(self, obj):
      review_data = ProductReview.objects.filter(products = obj.id)
      serialize = ProductReviewSerializers(review_data, many=True).data
      return serialize

   def get_image(self, obj):

      image_data = ProductImages.objects.filter(product=obj.id)
      image_serialize = ProductImagesSerializers(image_data, many=True).data
      return image_serialize

   def get_price(self, obj):
      data = ProductPrice.objects.filter(product = obj.id)
      serialize = BasicPriceSerializers(data, many=True).data
      if serialize:
         #print('price_details',serialize[0]['product_price'])
         return serialize[0]['product_price']

   class Meta:
      model = Product
      fields = '__all__'


class PincodeSerializer(serializers.ModelSerializer):
   class Meta:
       model = Pincodes
       fields = "__all__"
   # def create(self,data):
   #    instance = data
   #    return instance


class AddressSerializer(serializers.ModelSerializer):
   class Meta:
       model = Address
       fields = "__all__"
       #depth=1


class AdminBrandSerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductBrand
      fields = '__all__'



class AdmincategorySerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductCategory
      fields = '__all__'


class AdminSubcategorySerializer(serializers.ModelSerializer):
   class Meta:
      model = ProductSubCategory
      fields = '__all__'



class AdminSubcateTypeSerializer(serializers.ModelSerializer):
   category_name = serializers.SerializerMethodField()

   def get_category_name(self, obj):
      print(obj.id)
      data = ProductSubCategory.objects.filter(id = obj.sub_category_id).values()
      category = ProductCategory.objects.filter(id = data[0]['product_category_id']).values_list('product_category', flat=True)
      print(list(category)[0])
      return list(category)[0]
   class Meta:
      model = ProductSubCategoryType
      fields = '__all__'


class TagProductListSerializer(serializers.ModelSerializer):
   products = serializers.SerializerMethodField()

   def get_products(self, obj):
      products = Product.objects.filter(product_tags=obj)
      return ProductSerializers(products, many=True).data

   class Meta:
      model = Tags
      fields = ['id','tag','tag_desc','products']


class CategoryWithProductsSerializer(serializers.ModelSerializer):
   products = serializers.SerializerMethodField()

   class Meta:
      model = ProductCategory
      fields = ['id', 'product_category', 'products']

   def get_products(self, category):
      products = Product.objects.filter(
         product_sub_cat__product_category=category, ProductImages__isnull=False
         ).order_by('id').distinct()[:6]

      return ProductSerializers(products, many=True).data


class UserOrderDetailSerializer(serializers.ModelSerializer):
   product_name = serializers.SerializerMethodField()
   product_price_with_tax = serializers.SerializerMethodField()
   product_code = serializers.SerializerMethodField()
   product_image = serializers.SerializerMethodField()

   def get_product_image(self, obj):
      product = obj.product
      if product is None:
         return None
      first_image = product.ProductImages.first()
      if first_image:
         return first_image.product_image.url
      return None

   def get_product_name(self, obj):
        product = obj.product
        if product is None:
            return None
        return product.product_name

   def get_product_price_with_tax(self, obj):
      price = obj.product
      if price is None:
         return None
      return price.product_price_with_tax

   def get_product_code(self, obj):
      product_code = obj.product
      if product_code is None:
         return None
      return product_code.product_code

   class Meta:
      model = UserOrderDetail
      fields = '__all__'


class UserOrderSummarySerializer(serializers.ModelSerializer):
   order_details = UserOrderDetailSerializer(many=True)

   def to_representation(self, instance):
      data = super().to_representation(instance)
      user_data= instance.user
      address_data = instance.address
      additional_data = {
         "user_data":{
            "id":user_data.id,
            "first_name":user_data.first_name,
            "last_name":user_data.last_name,
            "phone_no":user_data.phone_no,
            "email":user_data.email,
         },
         "address_data":{
            "id" : address_data.id,
            "said" : address_data.addsaid,
            "service_area" : address_data.service_area,
            "address_one" : address_data.address_one,
            "address_two" : address_data.address_two,
            "pincode" : address_data.pincode,
            "city": address_data.city,
            "state" : address_data.state,
            "country" : address_data.country,
            "stid" : address_data.addstid,
            "ctid" : address_data.addctid,
         }
      }

      data['user'] = additional_data["user_data"]
      data['address'] = additional_data["address_data"]
      try:
         transaction = Transaction.objects.get(order_summary=instance)
         transaction_data = {
               "mihpayid": transaction.mihpayid,
               "mode": transaction.mode,
               "txnid": transaction.txnid,
               "addedon": transaction.addedon,
               "hash": transaction.hash,
               "bank_ref_num": transaction.bank_ref_num,
               "bankcode": transaction.bankcode,
               "transaction_status": transaction.transaction_status,
         }
         data['transaction'] = transaction_data
      except Transaction.DoesNotExist:
         data['transaction'] = None
      return data

   class Meta:
      model = UserOrderSummary
      fields = '__all__'

   def create(self, validated_data):
      order_details_data = validated_data.pop('order_details')

      transaction_data = {
            "mihpayid": self.initial_data.get('mihpayid'),
            "mode": self.initial_data.get("mode"),
            "txnid": self.initial_data.get("txnid"),
            "addedon": self.initial_data.get("addedon"),
            "hash": self.initial_data.get("hash"),
            "bank_ref_num": self.initial_data.get("bank_ref_num"),
            "bankcode": self.initial_data.get("bankcode"),
            "transaction_status": self.initial_data.get("status"),
        }

      order_summary = UserOrderSummary.objects.create(**validated_data)
      formatted_order_id = f"{order_summary.id:06d}"
      order_number = f"WEB{formatted_order_id}"
      order_summary.order_number = order_number
      order_summary.save()

      for order_detail_data in order_details_data:
         UserOrderDetail.objects.create(order_summary=order_summary, **order_detail_data)

      transaction = Transaction.objects.create(order_summary=order_summary, **transaction_data)
      return order_summary