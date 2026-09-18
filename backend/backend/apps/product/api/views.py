import base64
from datetime import date, timedelta
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import hashlib
import time
import os
from django.db.models import Sum, Q, Case, When, Value, IntegerField, F
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from accounts.models import User, create_username
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from rest_framework import viewsets
from product.models import ProductBrand, Product, ProductCart, ProductCategory, ProductFeedback, ProductImages, ProductPrice\
    , ProductRating, ProductReview, ProductSubCategory, HeaderScrollable, ShowRoom, Tags, ProductSubCategoryType\
    , Pincodes,Address, UserOrderDetail, UserOrderSummary, WishlistItem
from product.api.serializers import ProductBrandSerializers, ProductCartSerializers, ProductCategorySerializers, ProductFeedbackSerializers\
    , ProductImagesSerializers, ProductPriceSerializers, ProductRatingSerializers, ProductReviewSerializers, ProductSerializers\
        , ProductSubCategorySerializers, HeaderScrollableSerializers, ProductWishlistSerializer, ShowRoomSerializers, TagsSerializer\
        , ProductSubCategoryTypeSerializers, SubCategoryListSerializers, TypeFilterSerializers, ProductSearchSerializers,\
        PincodeSerializer, AddressSerializer, AdminBrandSerializer, AdmincategorySerializer, AdminSubcategorySerializer,\
        AdminSubcateTypeSerializer,TagProductListSerializer,CategoryWithProductsSerializer, UserOrderDetailSerializer, UserOrderSummarySerializer, ProductSerializerListDisplay

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
import json
import requests

import pandas as pd


class MediumResultsSetPagination(PageNumberPagination):
    page_size = 500
    page_size_query_param = 'page_size'
    max_page_size = 50000
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id') if not isinstance(queryset, list) else queryset
        return super().paginate_queryset(queryset, request, view)

class VeryLargeResultsSetPagination(PageNumberPagination):
    page_size = 90000
    page_size_query_param = 'page_size'
    max_page_size = 9000000
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id') if not isinstance(queryset, list) else queryset
        return super().paginate_queryset(queryset, request, view)


class LargeResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id')
        return super().paginate_queryset(queryset, request, view)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id')
        return super().paginate_queryset(queryset, request, view)

class SemiSmallResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id')
        return super().paginate_queryset(queryset, request, view)

class SmallResultsSetPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 150
    def paginate_queryset(self, queryset, request, view=None):
        queryset = queryset.order_by('id')
        return super().paginate_queryset(queryset, request, view)


class ProductListView(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    # serializer_class = ProductSerializers
    serializer_class = ProductSerializerListDisplay
    #permission_classes = [IsAuthenticated]
    pagination_class = MediumResultsSetPagination


class ProductView(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializers
    #permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=['get'], url_path='get-check-pincode',)
    @csrf_exempt
    def get_check_pincode(self, request, *args, **kwargs):
        id = self.get_object().id
        datas = Pincodes.objects.filter(id=1)
        pincodes = PincodeSerializer(datas, many=True).data
        #print(datas)
        if id%2==0:
            return Response(True)
        else:
            return Response(False)


class ProductBrandView(viewsets.ModelViewSet):
    queryset = ProductBrand.objects.all()
    serializer_class = ProductBrandSerializers
    pagination_class = LargeResultsSetPagination
    #permission_classes = [IsAuthenticated]

    # @action(detail=True, methods=['get'], url_path='get-product-list',)
    # @csrf_exempt
    # def get_product_list(self, request, *args, **kwargs):
    #     cat_id = self.get_object()
    #     result = ByBrandSerializers(instance=cat_id, context={'request': request}).data
    #     return Response({"result": result})


class ProductCategoryView(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializers
    #permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsSetPagination

    @action(detail=True, methods=['get'], url_path='get-subcat-list',)
    @csrf_exempt
    def get_subcat_list(self, request, *args, **kwargs):
        cat_id = self.get_object()
        result = SubCategoryListSerializers(instance=cat_id, context={'request': request}).data
        return Response({"result": result})



class ProductFeedbackView(viewsets.ModelViewSet):
    queryset = ProductFeedback.objects.all()
    serializer_class = ProductFeedbackSerializers
    #permission_classes = [IsAuthenticated]


class ProductImagesView(viewsets.ModelViewSet):
    queryset = ProductImages.objects.all()
    serializer_class = ProductImagesSerializers
    #permission_classes = [IsAuthenticated]

class ProductPriceView(viewsets.ModelViewSet):
    queryset = ProductPrice.objects.all()
    serializer_class = ProductPriceSerializers
    #permission_classes = [IsAuthenticated]


class ProductRatingView(viewsets.ModelViewSet):
    queryset = ProductRating.objects.all()
    serializer_class = ProductRatingSerializers
    #permission_classes = [IsAuthenticated]


class ProductReviewView(viewsets.ModelViewSet):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializers
    #permission_classes = [IsAuthenticated]


class ProductSubCategoryView(viewsets.ModelViewSet):
    queryset = ProductSubCategory.objects.all()
    serializer_class = ProductSubCategorySerializers
    #permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsSetPagination


class ProductSubCategoryTypeView(viewsets.ModelViewSet):
    queryset = ProductSubCategoryType.objects.all()
    serializer_class = ProductSubCategoryTypeSerializers
    #permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsSetPagination



class HeaderScrollableView(viewsets.ModelViewSet):
    queryset = HeaderScrollable.objects.all()
    serializer_class = HeaderScrollableSerializers
    #permission_classes = [IsAuthenticated]


# class UserOrdersView(viewsets.ModelViewSet):
#     queryset = UserOrders.objects.all()
#     serializer_class = UserOrdersSerializers
#     #permission_classes = [IsAuthenticated]


class ProductImageView(viewsets.ModelViewSet):
    queryset = ProductImages.objects.all()
    serializer_class = ProductImagesSerializers
    #permission_classes = [IsAuthenticated]


class ShowRoomeView(viewsets.ModelViewSet):
    queryset = ShowRoom.objects.all()
    serializer_class = ShowRoomSerializers
    #permission_classes = [IsAuthenticated]


class TagView(viewsets.ModelViewSet):
    queryset = Tags.objects.all()
    serializer_class = TagsSerializer
    #permission_classes = [IsAuthenticated]


class ProductSearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]

    def get_queryset(self):
        requested_key=self.kwargs['Productsearch']
        product_name_data=Product.objects.filter(product_name=requested_key)
        return product_name_data


class BrandSearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]
    def get_queryset(self):
        brand_id = ProductBrand.objects.filter(brand = self.kwargs['brandsearch']).values_list('id', flat=True)
        print(brand_id)
        data = Product.objects.filter(product_brand__in=brand_id)
        return data


class CategorySearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsSetPagination
    def get_queryset(self):
        cat_id = list(ProductCategory.objects.filter(product_category = self.kwargs['categorysearch']).values_list('id', flat=True))
        print(cat_id)
        if cat_id != []:
            product_data = Product.objects.filter(product_cat = cat_id[0])
            return product_data


class TagSearchView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]
    def get_queryset(self):
        isearch = self.kwargs['Tagsearch']
        print(isearch)
        product_data = Product.objects.filter(product_tags__icontains = isearch)
        return product_data


class PriceRangeView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]
    def get_queryset(self):
        prices=self.kwargs['price'].split('~')
        low_range = int(prices[0])
        high_range = int(prices[1])
        product_ids = ProductPrice.objects.filter(product_price__range= (low_range, high_range)).values_list('product', flat=True)
        print(product_ids)
        products = Product.objects.filter(id__in=product_ids)
        return products


class CartRegistView(viewsets.ModelViewSet):
    queryset = ProductCart.objects.all()
    serializer_class = ProductCartSerializers
    pagination_class = LargeResultsSetPagination
    #permission_classes = [IsAuthenticated]


class WishlistProductView(APIView):
    def post(self, request):
        user_id = request.data.get('user')
        product_id = request.data.get('product')

        if not user_id or not product_id:
            return Response("Both user_id and product_id are required.", status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            product = Product.objects.get(id=product_id)
        except (User.DoesNotExist, Product.DoesNotExist):
            return Response("User or Product does not exist.", status=status.HTTP_404_NOT_FOUND)

        wishlist_item, created = WishlistItem.objects.get_or_create(user=user, product=product)

        if created:
            serialized_wishlist = ProductWishlistSerializer(wishlist_item)
            return Response(serialized_wishlist.data, status=status.HTTP_201_CREATED)
        else:
            return Response("Product is already in the wishlist.", status=status.HTTP_200_OK)

    def get(self, request):
        user_id = request.query_params.get('user')

        if not user_id:
            return Response("User ID is required.", status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response("User does not exist.", status=status.HTTP_404_NOT_FOUND)

        wishlist_items = WishlistItem.objects.filter(user=user).order_by('-id')  # Replace 'id' with the field you want to order by

        paginator = SemiSmallResultsSetPagination()
        result_page = paginator.paginate_queryset(wishlist_items, request)

        serialized_products = ProductSerializers([item.product for item in result_page], many=True)
        return paginator.get_paginated_response(serialized_products.data)

    def delete(self, request):
        user_id = request.query_params.get('user')
        product_id = request.query_params.get('product')

        if not user_id or not product_id:
            return Response("Both user id and product id are required.", status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
            product = Product.objects.get(id=product_id)
        except (User.DoesNotExist, Product.DoesNotExist):
            return Response("User or Product does not exist.", status=status.HTTP_404_NOT_FOUND)

        try:
            wishlist_item = WishlistItem.objects.get(user=user, product=product)
            wishlist_item.delete()
            return Response("Product removed from wishlist.", status=status.HTTP_200_OK)
        except WishlistItem.DoesNotExist:
            return Response("Product was not in the wishlist.", status=status.HTTP_404_NOT_FOUND)



class CategoryPaginationView(generics.ListAPIView):
    serializer_class = ProductSearchSerializers
    #permission_classes = [IsAuthenticated]
    #pagination_class = LargeResultsSetPagination
    def get_queryset(self):
        cat_id = list(ProductCategory.objects.filter(product_category = self.kwargs['categorysearch']).values_list('id', flat=True))
        print(cat_id)
        if cat_id != []:
            product_data = Product.objects.filter(product_cat = cat_id[0])
            return product_data


@api_view(['post', 'get'])
@csrf_exempt
def PincodeValidation(request):

    if request.method == 'POST':
        dic = request.data
        pincode = dic['pincode_list']
        print(type(pincode))
        datas = Pincodes.objects.all()
        serialize = PincodeSerializer(datas, many=True).data
        if int(pincode) in serialize[0]['pincode_list']['pincodes']:
            return Response('Delivery in 3-4  days')
        else:
            return Response('Not available in your pincode')
    if request.method == 'GET':
        return Response("no validation found")


class AddressView(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    serializer_class = AddressSerializer
    queryset = Address.objects.all()
    pagination_class = LargeResultsSetPagination


class AdminBrandView(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    serializer_class = AdminBrandSerializer
    queryset = ProductBrand.objects.all()
    pagination_class = LargeResultsSetPagination


class AdminProductView(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    serializer_class = AdmincategorySerializer
    queryset = ProductCategory.objects.all()
    pagination_class = LargeResultsSetPagination


class AdminSubCatView(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    serializer_class = AdminSubcategorySerializer
    queryset = ProductSubCategory.objects.all()
    pagination_class = LargeResultsSetPagination


class AdminSubcatTypeView(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'head', 'patch', 'delete']
    serializer_class = AdminSubcateTypeSerializer
    queryset = ProductSubCategoryType.objects.all()
    pagination_class = LargeResultsSetPagination


@api_view(['post'])
@csrf_exempt
def user_address(request):
    data=request.data
    print(data['user'])
    addressdata = Address.objects.filter(user=data['user']).values()
    userdata = User.objects.filter(id=data['user']).values()
    mainaddress = userdata[0]
    mainaddress = {'first_name':mainaddress['first_name'],'last_name':mainaddress['last_name']
                   ,'country':mainaddress['country'],'pincode':mainaddress['pincode'],'city':mainaddress['city'],
                   'phone_no':mainaddress['phone_no'], 'email_address':mainaddress['email'],'service_area':'H',
                   'user_id':mainaddress['id'], 'address_one':mainaddress['address_one'], 'address_two':mainaddress['address_two']}
    print(userdata[0])
    return Response({'mainaddress':mainaddress,'sub_addresses':addressdata})


# @api_view(['get'])
# @csrf_exempt
# def product_inserter(request):
#     for count in range(0,25793,250):
#         product = requests.get(f'http://chhabriasons.sixorbit.com/?urlq=service&version=1.0&key=123&task=variation/fetch&user_id=410002661&access_token=6706619512258332164&last_updated&limit=&searchtext&limit_bit=1&default_limit=250&limit={count}')
#         datas = json.loads(product.text)
#         datas = [datas]

#         for records in datas:

#             record=records['data']['variations']
#             for data in record:
#                 #print(data)
#                 if data.get('attributes') == None:
#                     print(data['isvid'])

#                     print('attributes not exist')

#                 else:
#                     attribute = data['attributes']
#                     brand_data = ProductBrand.objects.filter(brand_id_erp=int(data['brand_id'])).values()
#                     subcat_id = ProductSubCategory.objects.filter(Erp_Subcategory_id = data['category_id']).values()
#                     print('loop range',count)
#                     try:
#                         subcat_id=subcat_id[0]['id']
#                     except:
#                         subcat_id = None

#                     try:
#                         brand_id = brand_data[0]['id']
#                     except:
#                         brand_id = None
#                     color,p_cat,l_inch,b_inch,l_mm,b_mm,o_sizeI,o_sizeM,web,l_time,liqud = 0,0,0,0,0,0,0,0,0,0,0

#                     for attr in attribute:
#                         if 'Color' in attr.values():
#                             color=attr['attr_value']
#                         elif 'Parent_Category' in  attr.values():
#                             p_cat = attr['attr_value']
#                         elif 'length in inches' in  attr.values():
#                             l_inch = attr['attr_value']
#                         elif 'breadth OR width in mm' in  attr.values():
#                             b_inch = attr['attr_value']
#                         elif 'length in mm' in  attr.values():
#                             l_mm = attr['attr_value']
#                         elif 'breadth OR width in mm' in  attr.values():
#                             b_mm = attr['attr_value']
#                         elif 'overall size in inches' in  attr.values():
#                             o_sizeI = attr['attr_value']
#                         elif 'overall size in mm' in  attr.values():
#                             o_sizeM = attr['attr_value']
#                         elif 'Website' in  attr.values():
#                             web = attr['attr_value']
#                         elif 'lead time in days' in  attr.values():
#                             l_time = attr['attr_value']
#                         elif 'liquidation sku yes no ' in attr.values():
#                             liqud = attr['attr_value']
#                     for attr in attribute:
#                         if 'Website' in attr.values():
#                             if attr['attr_value'] == 'YES':
#                                 product_instance = Product.objects.create(
#                                     product_sub_cat_id = subcat_id,
#                                     subcategorytype_id_id = None,
#                                     product_name = data['variation_name'],
#                                     product_code = data['variation_number'],
#                                     product_color = color,
#                                     product_dimension = None,
#                                     product_shape = None,
#                                     product_finish = None,
#                                     product_themes = None,
#                                     product_tags = None,
#                                     header_scrollable_id = None,
#                                     product_brand_id = brand_id,
#                                     related_products = None,
#                                     product_showrooms = None,
#                                     is_wishlisted = True,
#                                     variations = None,
#                                     item_id = data['variation_number'],
#                                     sku_name = data['sku'],
#                                     hsn_code = data['hsn_code'],
#                                     bar_code = data['barcode'],
#                                     uom = data.get('measured_unit'),
#                                     length_in_inches = l_inch,
#                                     breadth_in_inches = b_inch,
#                                     length_in_mm = l_mm,
#                                     breadth_in_mm = b_mm,
#                                     overall_size_in_inches = o_sizeI,
#                                     overall_size_in_mm = o_sizeM,
#                                     lead_time = l_time,
#                                     total_stock = data['stock_availability'],
#                                     liqudation = liqud

#                                 )

#     return Response('the product records successfully insert in ')

@api_view(['get'])
@csrf_exempt
def product_inserter(request):
    for count in range(0, 999999, 250):
        product = requests.get(f'http://chhabriasons.sixorbit.com/?urlq=service&version=1.0&key=123&task=variation/fetch&user_id=410002661&access_token=6613527815757554180&last_updated&limit=&searchtext&limit_bit=1&default_limit=250&limit={count}')
        datas = json.loads(product.text)
        if datas.get("success",''):
            variations = datas['data']['variations']
            for data in variations:
                attributes = data.get('attributes', [])
                print("entering ",count)
                website_attribute = next((attr for attr in attributes if attr.get('attr_name') == 'Website' and attr.get('attr_value') == 'YES'), None)
                if website_attribute is not None:
                    brand_data = ProductBrand.objects.filter(brand_id_erp=int(data['brand_id'])).values()
                    subcat_id = ProductSubCategory.objects.filter(Erp_Subcategory_id=data['category_id']).values()
                    try:
                        subcat_id = subcat_id[0]['id']
                    except:
                        subcat_id = None
                    try:
                        brand_id = brand_data[0]['id']
                    except:
                        brand_id = None

                    color, design, l_inch, b_inch,h_inch, h_mm, l_mm, b_mm, o_sizeI, o_sizeM, l_time, liqud = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

                    for attr in attributes:
                        if 'Color' in attr.get('attr_name', ''):
                            color = attr.get('attr_value', None)
                        if 'design' in attr.get('attr_name', ''):
                            design = attr.get('attr_value', None)
                        if 'length in inches' in attr.get('attr_name', ''):
                            l_inch = attr.get('attr_value', None)
                        if 'breadth OR width in inches' in attr.get('attr_name', ''):
                            b_inch = attr.get('attr_value', None)
                        if 'height OR thickness in inches' in attr.get('attr_name', ''):
                            h_inch = attr.get('attr_value', None)
                        if 'length in mm' in attr.get('attr_name', ''):
                            l_mm = attr.get('attr_value', None)
                        if 'breadth OR width in mm' in attr.get('attr_name', ''):
                            b_mm = attr.get('attr_value', None)
                        if 'height OR thickness in mm' in attr.get('attr_name', ''):
                            h_mm = attr.get('attr_value', None)
                        if 'overall size in inches' in attr.get('attr_name', ''):
                            o_sizeI = attr.get('attr_value', None)
                        if 'overall size in mm' in attr.get('attr_name', ''):
                            o_sizeM = attr.get('attr_value', None)
                        if 'lead time in days' in attr.get('attr_name', ''):
                            l_time = attr.get('attr_value', None)
                        if 'liquidation sku yes no' in attr.get('attr_name', ''):
                            liqud = attr.get('attr_value', None)

                    try:
                        product_instance = Product.objects.create(
                            product_sub_cat_id=subcat_id,
                            subcategorytype_id_id=None,
                            product_name=data['variation_name'],
                            product_code=data['variation_number'],
                            product_color=color,
                            product_design = design,
                            product_weight = data['weight'],
                            product_shape=None,
                            product_finish=None,
                            product_themes=None,
                            header_scrollable_id=None,
                            product_brand_id=brand_id,
                            related_products=None,
                            product_showrooms=None,
                            is_wishlisted=True,
                            variations=None,
                            item_id=data['variation_number'],
                            sku_name=data['sku'],
                            hsn_code=data['hsn_code'],
                            bar_code=data['barcode'],
                            uom=data.get('measured_unit'),
                            length_in_inches=l_inch,
                            breadth_in_inches=b_inch,
                            height_in_inches=h_inch,
                            length_in_mm=l_mm,
                            breadth_in_mm=b_mm,
                            height_in_mm = h_mm,
                            overall_size_in_inches=o_sizeI,
                            overall_size_in_mm=o_sizeM,
                            lead_time=l_time,
                            total_stock=data['stock_availability'],
                            liqudation=liqud,
                            product_price_with_tax = data['price_with_tax'],
                            product_tax = data['tax'],
                            product_max_discount_percent = data['max_discount_percent'],
                            created_at = timezone.now()
                        )
                        product_instance.product_tags.set([])
                    except Exception as e:
                        print(f"Error inserting product: {e}")
        else:
            break
    return Response('The product records were successfully inserted.')
    # return Response(variations, content_type='json/application')




@api_view(['get'])
@csrf_exempt
def brand_insert(request):
    brand_data = requests.get("http://chhabriasons.sixorbit.com/?urlq=service&version=1.0&key=123&task=variation/fetch_brand&user_id=410002661&access_token=6613527815757554180")
    brand_data = brand_data.text
    brand_json = json.loads(brand_data)
    brand_dict = dict(brand_json)
    brand_list=brand_dict["data"]["brand"]
    for brands in brand_list:
        brand_instance = ProductBrand.objects.create(
            brand_id_erp = brands['bid'],
            brand = brands['name'],
            brand_desc = brands['description'],
            brand_max_discount = brands['max_discount']
        )
    return Response(brand_list, content_type='json/application')



@api_view(['get'])
@csrf_exempt
def category_insert(request):
    data = pd.read_json('categorys.json')
    for records in data:
        if records == 'data':
            df = pd.DataFrame(data[records]['category'])
            cat_df=df[df['main_parent'] == '0']
            for name,desc,catid in zip(cat_df['name'],cat_df['description'],cat_df['catid']):
                print(name, desc,catid)
                category_instance = ProductCategory.objects.create(
                    product_category = name,
                    product_category_desc = desc,
                    Erp_category_id = catid
                )

    return Response('category data inserted')


@api_view(['get'])
@csrf_exempt
def subcategory_insert(request):
    data = pd.read_json('categorys.json')
    for records in data:
        if records == 'data':
        #print(data[records]['category'])
            df = pd.DataFrame(data[records]['category'])
            cat_df=df[df['main_parent'] == '0']
            #print(cat_df)
            sub_cat_df = df[(df['main_parent'].isin(cat_df['catid']))]
            for name,desc,catid,main_p in zip(sub_cat_df['name'],sub_cat_df['description'],sub_cat_df['catid'],sub_cat_df['main_parent']) :
                #trying to assign foreign reference to the  subcategory
                category_FK = ProductCategory.objects.filter(Erp_category_id = main_p).values()
                print(category_FK[0]['id'])
                subcategory_instance = ProductSubCategory.objects.create(
                    product_category_id = category_FK[0]['id'],
                    product_sub_category = name,
                    product_subcategory_desc = desc,
                    Erp_Subcategory_id = catid
                )

    return Response('subcategoryinserted')


@api_view(['GET'])
@csrf_exempt
def product_updater(request):
    fetched_at = request.GET.get('fetched_at', None)
    if fetched_at:
        try:
            fetched_at = timezone.datetime.fromisoformat(fetched_at)
        except ValueError:
            return Response("Invalid 'last_updated' parameter format.", status=status.HTTP_400_BAD_REQUEST)
    else:
        fetched_at = timezone.now() - timedelta(days=1)
    response = requests.get(f'http://chhabriasons.sixorbit.com//?urlq=service&version=1.0&key=123&task=variation/fetch&user_id=410002661&access_token=6613527815757554180&last_updated={fetched_at}&limit=250&searchtext&limit_bit=1')
    datas = json.loads(response.text)
    # data = pd.read_json('product.json')
    variations = datas['data']['variations']
    print(variations)
    for data in variations:
        variation_num = data.get('variation_number')
        try:
            product = Product.objects.get(product_code=variation_num)
        except Product.DoesNotExist:
            product=None

        if product:
            print(f'the product exist {variation_num} ')

            # if the product exists but the updated data does not have Website attr, then delete the product

            # website_attribute = next((attr for attr in data.get('attributes', []) if attr.get('attr_name') == 'Website' and attr.get('attr_value') == 'YES'), None)
            # if not website_attribute:
            #     print(f'Deleting product: {variation_num}')
            #     product.delete()

            # else:
            #     print(f'Updating product: {variation_num}')

            try:
                product_subcategory = ProductSubCategory.objects.get(Erp_Subcategory_id=data['category_id'])
            except ProductSubCategory.DoesNotExist:
                product_subcategory = None
            try:
                brand_data = ProductBrand.objects.get(brand_id_erp=int(data['brand_id']))
            except ProductSubCategory.DoesNotExist:
                product_subcategory = None

            tag_ids = data.get('product_tags', [])  # Replace 'tag_ids' with the actual field name in your data

            if tag_ids is not []:
                tags_to_associate = Tags.objects.filter(id__in=tag_ids)

            product_attributes = {attr['attr_name']: attr['attr_value'] for attr in data.get('attributes', [])}

            product.product_sub_cat = product_subcategory
            product.product_name = data['variation_name'],
            product.product_color = product_attributes.get('Color', None)
            product.product_design = product_attributes.get('design', None)
            product.product_weight = data['weight']
            product.product_shape = data.get('product_shape',None)
            product.product_finish = data.get('product_finish', None)
            product.product_themes= data.get('product_themes',None)
            product.header_scrollable = data.get('header_scrollable',None)
            product.product_brand = brand_data
            product.related_products = data.get('related_product', None)
            product.product_showrooms = data.get('product_showrooms', None)
            product.is_wishlisted = data.get('is_wishlisted' , False)
            product.variations = data.get('variations', None)
            product.item_id = data['variation_number']
            product.sku_name = data['sku']
            product.hsn_code = data['hsn_code']
            product.bar_code = data['barcode']
            product.uom=data.get('measured_unit', None)
            product.length_in_inches = product_attributes.get('length in inches')
            product.breadth_in_inches = product_attributes.get('breadth OR width in inches', None)
            product.height_in_inches = product_attributes.get('height OR thickness in inches', None)
            product.overall_size_in_inches = product_attributes.get('overall size in inches', None)
            product.length_in_mm = product_attributes.get('length in mm', None)
            product.breadth_in_mm = product_attributes.get('breadth OR width in mm',None)
            product.height_in_mm = product_attributes.get('height OR thickness in mm', None)
            product.overall_size_in_mm = product_attributes.get('overall size in mm', None)
            product.lead_time = product_attributes.get('lead time in days', None)
            product.liqudation = product_attributes.get('liquidation sku yes no', None)
            product.total_stock =data['stock_availability']
            product.product_price_with_tax = data['price_with_tax']
            product.product_tax = data['tax']
            product.product_max_discount_percent = data['max_discount_percent']
            product.product_tags.set(tags_to_associate)
            product.updated_at = timezone.now()
            product.save()
        else:
            attributes = data.get('attributes', [])
            website_attribute = next((attr for attr in attributes if attr.get('attr_name') == 'Website' and attr.get('attr_value') == 'YES'), None)
            if website_attribute is not None:
                print(f'the product does not exist ----> {variation_num}')
                brand_data = ProductBrand.objects.filter(brand_id_erp=int(data['brand_id'])).values()
                subcat_id = ProductSubCategory.objects.filter(Erp_Subcategory_id=data['category_id']).values()
                try:
                    subcat_id = subcat_id[0]['id']
                except:
                    subcat_id = None
                try:
                    brand_id = brand_data[0]['id']
                except:
                    brand_id = None

                color, design, l_inch, b_inch,h_inch, h_mm, l_mm, b_mm, o_sizeI, o_sizeM, l_time, liqud = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

                for attr in attributes:
                    if 'Color' in attr.get('attr_name', ''):
                        color = attr.get('attr_value', None)
                    if 'design' in attr.get('attr_name', ''):
                        design = attr.get('attr_value', None)
                    if 'length in inches' in attr.get('attr_name', ''):
                        l_inch = attr.get('attr_value', None)
                    if 'breadth OR width in inches' in attr.get('attr_name', ''):
                        b_inch = attr.get('attr_value', None)
                    if 'height OR thickness in inches' in attr.get('attr_name', ''):
                        h_inch = attr.get('attr_value', None)
                    if 'length in mm' in attr.get('attr_name', ''):
                        l_mm = attr.get('attr_value', None)
                    if 'breadth OR width in mm' in attr.get('attr_name', ''):
                        b_mm = attr.get('attr_value', None)
                    if 'height OR thickness in mm' in attr.get('attr_name', ''):
                        h_mm = attr.get('attr_value', None)
                    if 'overall size in inches' in attr.get('attr_name', ''):
                        o_sizeI = attr.get('attr_value', None)
                    if 'overall size in mm' in attr.get('attr_name', ''):
                        o_sizeM = attr.get('attr_value', None)
                    if 'lead time in days' in attr.get('attr_name', ''):
                        l_time = attr.get('attr_value', None)
                    if 'liquidation sku yes no' in attr.get('attr_name', ''):
                        liqud = attr.get('attr_value', None)

                try:
                    product_instance = Product.objects.create(
                        product_sub_cat_id=subcat_id,
                        subcategorytype_id_id=None,
                        product_name=data['variation_name'],
                        product_code=data['variation_number'],
                        product_color=color,
                        product_design = design,
                        product_weight = data['weight'],
                        product_shape=None,
                        product_finish=None,
                        product_themes=None,
                        header_scrollable_id=None,
                        product_brand_id=brand_id,
                        related_products=None,
                        product_showrooms=None,
                        is_wishlisted=True,
                        variations=None,
                        item_id=data['variation_number'],
                        sku_name=data['sku'],
                        hsn_code=data['hsn_code'],
                        bar_code=data['barcode'],
                        uom=data.get('measured_unit'),
                        length_in_inches=l_inch,
                        breadth_in_inches=b_inch,
                        height_in_inches=h_inch,
                        length_in_mm=l_mm,
                        breadth_in_mm=b_mm,
                        height_in_mm = h_mm,
                        overall_size_in_inches=o_sizeI,
                        overall_size_in_mm=o_sizeM,
                        lead_time=l_time,
                        total_stock=data['stock_availability'],
                        liqudation=liqud,
                        product_price_with_tax = data['price_with_tax'],
                        product_tax = data['tax'],
                        product_max_discount_percent = data['max_discount_percent'],
                        created_at = timezone.now()
                    )
                    product_instance.product_tags.set([])
                except Exception as e:
                    print(f"Error inserting product: {e}")
    return Response(variations, content_type='json/application')


# class PaymentRequestView(viewsets.ModelViewSet):
#     queryset = Payment.objects.all()
#     serializer_class = PaymentSerializer
#     http_method_names = ['get', 'post']

#     def create(self, request, *args, **kwargs):
#         user_id = request.data.get("id")
#         try:
#             user = User.objects.get(id=user_id)
#         except User.DoesNotExist:
#             return Response({"message": "User not found. "}, status=status.HTTP_404_NOT_FOUND)

#         if user.is_verified:
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#             serializer.save(user=user)

#             response_data = {
#                 "message": "Payment successful, happy shopping!",
#                 "data": serializer.data
#             }
#             return Response(response_data, status=status.HTTP_201_CREATED)
#         else:
#             return Response({"message": "User is not verified. Payment failed"},
#                             status=status.HTTP_401_UNAUTHORIZED)


class TagsListWithProductsView(viewsets.ModelViewSet):
    serializer_class = TagProductListSerializer
    def get_queryset(self):
        return Tags.objects.filter(products__isnull=False).distinct()

    @action(detail=True, methods=['GET'] , url_path='tags-products-list')
    def tags(self, request, pk=None):
        tags = self.get_object()
        serializer = self.get_serializer(tags)
        return Response(serializer.data)

class CategoriesWithProductsView(viewsets.ReadOnlyModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = CategoryWithProductsSerializer

class TotalProductsView(APIView):
    def get(self, request):
        today = date.today()
        # start_date = timezone.now() - timedelta(days=1)
        total_products = Product.objects.count()
        newly_added_product_count = Product.objects.filter(created_at__gte=today).count()
        recently_updated_product_count = Product.objects.filter(updated_at__gte=today).count()
        newly_added_or_updated_products = Product.objects.filter(Q(created_at__gte=today) | Q(updated_at__gte=today)).distinct().count()
        message = {
            'total_products':total_products,
            'newly_added_product_count':newly_added_product_count,
            'recently_updated_product_count':recently_updated_product_count,
            'newly_added_or_updated_products':newly_added_or_updated_products
        }
        return Response(message, status=200)

class TotalBrandsView(APIView):
    def get(self, request):
        total_brands = ProductBrand.objects.count()
        return Response({'total_brands': total_brands})

@api_view(['GET'])
def orders_statistics(request):
    today = date.today()
    try:
        orders_today = UserOrderSummary.objects.filter(ordered_date=today).count()
        total_orders = UserOrderSummary.objects.all().count()
        total_value_today = UserOrderSummary.objects.filter(ordered_date=today).aggregate(Sum('total_amt'))['total_amt__sum'] or 0.0
        total_collection = UserOrderSummary.objects.all().aggregate(Sum('total_amt'))['total_amt__sum'] or 0.0

        message = {
            'daily_order_count':orders_today,
            'daily_order_value':total_value_today,
            'total_orders':total_orders,
            'total_collection':total_collection
        }
        return Response(message,status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['POST',])
def initiate_payment(request):
    merchant_key = os.getenv('PAYU_MERCHANT_KEY')
    salt = os.getenv('PAYU_SALT_KEY')

    print("merchant-->",merchant_key,"salt-->", salt)
    payment_data = request.data
    product_name = json.loads(payment_data.get('product_name', '[]'))
    product_info = '|'.join([str(products['product']) for products in product_name])
    print(product_info)
    user_id = payment_data['user_id']
    current_datetime = time.strftime('%Y%m%d%H%M%S')
    txnid = f"{user_id}{current_datetime}"
    hash_string = f"{merchant_key}|{txnid}|{payment_data['amount']}|{product_info}|{payment_data['firstname']}|{payment_data['email']}|||||||||||{salt}"
    hash_value = hashlib.sha512(hash_string.encode('utf-8')).hexdigest()

    payu_request_data = {
        'key': merchant_key,
        'txnid': txnid,
        'productinfo': product_info,
        'amount' : payment_data['amount'],
        # 'amount' : '110.00',
        'email' : payment_data['email'],
        'firstname' : payment_data['firstname'],
        'phone' : payment_data['phone'],
        'surl' :  os.getenv('SURL'),
        'furl' : 'https://chabsons.com/payment/failure',
        'hash': hash_value,
    }
    print("surl-->",os.getenv('SURL'))

    payu_payment_url =  os.getenv('PAYU_URL')
    print("payu_payment_url-->", payu_payment_url)

    response = requests.post(payu_payment_url, data=payu_request_data)

    if response.status_code == 200:
        return Response({'paymentUrl': response.url}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Payment initiation failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def confirm_payment(request):

    data = request.data

    mihpayid = data.get("mihpayid")
    txnid = data.get("txnid")
    addedon = data.get("addedon")
    hash = data.get("hash")
    bank_ref_num = data.get("bank_ref_num")
    bankcode = data.get("bankcode")
    mode = data.get("mode")
    key = data.get("key")
    transaction_status = data.get('status')

    params = {
        'mihpayid': mihpayid,
        'txnid': txnid,
        'addedon': addedon,
        'bank_ref_num': bank_ref_num,
        'bankcode': bankcode,
        'mode': mode,
        'key': key,
        'hash': hash,
        'status' : transaction_status,
    }

    # print(params)
    # return Response(params)

    data_string = "|".join([f"{key}={value}" for key, value in params.items()])
    encoded_data = base64.b64encode(data_string.encode()).decode()
    redirect_url = f'https://chabsons.com/successpage/?meparams={encoded_data}'
    return redirect(redirect_url)


class UserOrderSummaryView(viewsets.ModelViewSet):
    queryset = UserOrderSummary.objects.all()
    serializer_class = UserOrderSummarySerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user_id = self.request.query_params.get('user')
        if user_id:
            return UserOrderSummary.objects.filter(user=user_id)
        return UserOrderSummary.objects.all()

class UserOrderDetailView(viewsets.ModelViewSet):
    queryset = UserOrderDetail.objects.all()
    serializer_class = UserOrderDetailSerializer

class BrandWithProductsView(viewsets.ReadOnlyModelViewSet):
    queryset = ProductBrand.objects.all()
    serializer_class = ProductSerializers
    pagination_class = SemiSmallResultsSetPagination
    def get_queryset(self):
        brand_id = self.kwargs['brand_id']
        return Product.objects.filter( ProductImages__isnull=False, product_brand__id=brand_id).distinct()

class CatSubcatListView(APIView):
    def get(self, request, format=None):
        categories = ProductCategory.objects.all()
        category_data = []

        for category in categories:
            subcategory = category.category.all()
            if subcategory.exists():
                category_data.append({
                    'id': category.id,
                    'product_category': category.product_category,
                    'product_category_desc': category.product_category_desc,
                    'Erp_category_id': category.Erp_category_id,
                    'subMenu': ProductSubCategorySerializers(subcategory, many=True).data
                })

        return Response(category_data)


class SubCategoryProductListView(APIView):
    def get(self, request,id=None,format=None):
        if id is not None:
            try:
                subcategory = ProductSubCategory.objects.get(id=id)
            except ProductSubCategory.DoesNotExist:
                return Response({"message": "Subcategory not found"}, status=404)

            products = subcategory.subcategory_names.filter(ProductImages__isnull=False)

            if products.exists():
                subcategory_data = {
                    'subcategory_id': subcategory.id,
                    'subcategory_name': subcategory.product_sub_category,
                    'product_subcategory_desc': subcategory.product_subcategory_desc,
                    'Erp_Subcategory_id': subcategory.Erp_Subcategory_id,
                    'products': ProductSerializers(products, many=True).data
                }
                return Response(subcategory_data)
            else:
                return Response({"message": "No products found for this subcategory"}, status=404)
        else:
            subcategory_data = []
            try:
                subcategories = ProductSubCategory.objects.all()
            except ProductSubCategory.DoesNotExist:
                return Response({"message": "Subcategory not found"}, status=404)

            for subcategory in subcategories:
                products = subcategory.subcategory_names.filter(ProductImages__isnull=False)
                if products.exists():
                    subcategory_data.append({
                        'subcategory_id': subcategory.id,
                        'subcategory_name': subcategory.product_sub_category,
                        'product_subcategory_desc' :subcategory.product_subcategory_desc,
                        'Erp_Subcategory_id' : subcategory.Erp_Subcategory_id,
                        'products': ProductSerializers(products, many=True).data
                    })

            return Response(subcategory_data)


class AllSearchView(generics.ListAPIView):
    serializer_class = ProductSerializers
    pagination_class = SmallResultsSetPagination

    def get_queryset(self):
        search_query = self.request.query_params.get('q', '')

        queryset = Product.objects.filter(
            Q(product_name__icontains=search_query) |
            Q(product_brand__brand__icontains=search_query) |
            Q(product_tags__tag__icontains=search_query) |
            Q(product_sub_cat__product_sub_category__icontains=search_query) |
            Q(product_sub_cat__product_category__product_category__icontains=search_query)
        ).annotate(
            relevance=Case(
                When(Q(product_name__icontains=search_query), then=Value(4)),
                When(Q(product_brand__brand__icontains=search_query), then=Value(3)),
                When(Q(product_tags__tag__icontains=search_query), then=Value(2)),
                When(Q(product_sub_cat__product_category__product_category__icontains=search_query), then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).distinct()

        queryset = queryset.filter(ProductImages__isnull=False).order_by('-relevance')

        return queryset

class ProductNameListView(APIView):
    def get(self, request, format=None):
        try:
            product_names = Product.objects.filter(ProductImages__isnull=False).values_list('product_name', flat=True)

            product_names_list = list(product_names)

            return Response(product_names_list, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetStatesView(APIView):
    def get(self, request, format=None):
        try:

            response = requests.get(f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=user%2Ffetch_countries_states&user_id=410002661&access_token=6613527815757554180')
            datas = json.loads(response.text)
            states = datas['data']['states_countries']
            output_dict = [x for x in states if x['ctid'] == "1"]

            return Response(output_dict, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetCitiesView(APIView):
    def get(self, request, format=None):
        try:
            state_param = request.GET.get('stid', None)
            if state_param:
                response = requests.get(f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=user/fetch_cities&user_id=410002661&access_token=6613527815757554180&ctid=1&stid={state_param}')
            else:
                response = requests.get(f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=user/fetch_cities&user_id=410002661&access_token=6613527815757554180&ctid=1&stid=304')
            datas = json.loads(response.text)
            cities = datas['data']['cities']

            return Response(cities, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.db.models import Count
class DuplicateProductListView(generics.ListAPIView):
    serializer_class = ProductSerializers

    def get_queryset(self):
        duplicate_products = Product.objects.values('product_code').annotate(count=Count('product_code')).filter(count__gt=1)
        return Product.objects.filter(product_code__in=[product['product_code'] for product in duplicate_products])


class AllProductListView(APIView):

    def get(self, request, *args, **kwargs):
        minio_base_url = os.getenv('MINIO_ACCESS_URL')

        products = Product.objects.select_related(
            'product_sub_category__product_category', 'product_brand','product_tags'
        ).prefetch_related(
            'ProductImages'
        ).values(
            'id',
            'product_name',
            'product_price_with_tax',
            'product_code',
            'sku_name',
            'product_color',
            image=F('ProductImages__product_image'),
            product_cat=F('product_sub_cat__product_category__product_category'),
            brand=F('product_brand__brand'),
            product_sub_category=F('product_sub_cat__product_sub_category'),
        ).distinct('id')


        # Serialize the tags for each product
        # serialized_products = []

        # for product in products:
        #     tags_data = []
        #     if 'product_tags' in product:
        #         tags_data = TagsSerializer(Tags.objects.filter(id__in=product['product_tags']), many=True).data
        #     product['product_tags'] = tags_data
        #     serialized_products.append(product)
            # Construct the full Minio URL by combining the base URL and the relative image path
        serialized_products = []

        for product in products:
            if product['image'] is not None:
                current_protocol = 'https' if request.is_secure() else 'http'
                product['image'] = f"{current_protocol}://{minio_base_url}/{str(product['image'])}"
            serialized_products.append(product)

        return JsonResponse({'products':serialized_products})
        # paginator = VeryLargeResultsSetPagination()
        # paginated_products = paginator.paginate_queryset(serialized_products, request, view=self)
        # return paginator.get_paginated_response({'products': paginated_products})

class ProductListInCategory(viewsets.ModelViewSet):
    serializer_class = ProductSerializers
    pagination_class = SemiSmallResultsSetPagination

    def get_queryset(self):
        category_id = self.request.query_params.get('category_id')
        if category_id is not None:
            try:
                category_id = int(category_id)
                return Product.objects.filter( ProductImages__isnull=False, product_sub_cat__product_category=category_id).distinct()
            except ValueError:
                return Product.objects.none()
        else:
            return Product.objects.none()

class ProductListInSubCategory(viewsets.ModelViewSet):
    serializer_class = ProductSerializers
    pagination_class = SemiSmallResultsSetPagination

    def get_queryset(self):
        sub_category_id = self.request.query_params.get('subcat_id')
        if sub_category_id is not None:
            try:
                sub_category_id = int(sub_category_id)
                return Product.objects.filter( ProductImages__isnull=False, product_sub_cat_id=sub_category_id).distinct()
            except ValueError:
                return Product.objects.none()
        else:
            return Product.objects.none()

@api_view(['GET'])
def get_product_colour(request):
    if request.method == 'GET':
        colors = Product.objects.values_list('product_color', flat=True).distinct()
        color_list = list(colors)
        return JsonResponse({'colors': color_list}, safe=False)
