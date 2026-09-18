from rest_framework import serializers
from ERPintegration.models import ProductInErp, ERPUser
import  json
import requests

class ErpProductSerailzier(serializers.ModelSerializer):
    

    class Meta:
        model = ProductInErp
        fields = '__all__'
    
    def create(self, validated_data):
        print('hello world')
        response_API = requests.get('http://chhabriasons.sixorbit.com/?urlq=service&version=1.0&key=123&task=variation/fetch&user_id=410002661&access_token=6706619512258332164&last_updated&limit=&searchtext')
        # print(type(response_API))
        records = response_API.text
        records = json.loads(records)
        records = records['data']
        records = records['variations']
    
        for data in records:
            print(data)

            v_code = None
            if data['vendor_code'] != '' and data['vendor_code'] != ' ' :
                v_code = data['vendor_code']
            
            r_code = None
            if data['rack_code'] != '' and data['rack_code'] != ' ' :
                v_code = data['rack_code']
            
            productinerp_instance = ProductInErp.objects.create(
                isvid=data['isvid'],
                variation_number=data['variation_number'],
                variation_name=data['variation_name'],
                sku=data['sku'],
                hsn_code=data['hsn_code'],
                meaid=data['meaid'],
                unit=data['unit'],
                item_type=data['item_type'],
                brand=data['brand'],
                brand_id=data['brand_id'],
                category_id=data['category_id'],
                category=data['category'],
                parent_category_id=data['parent_category_id'],
                parent_category=data['parent_category'],
                main_category_id=data['main_category_id'],
                main_category=data['main_category'],
                volume=data['volume'],
                weight=data['weight'],
                tax=data['tax'],
                price=data['price'],
                default_vendor=data['default_vendor'],
                vendor_code=v_code,
                product_type=data['product_type'],
                min_discount_percent=data['min_discount_percent'],
                max_discount_percent=data['max_discount_percent'],
                purchase_price=data['purchase_price'],
                package_quantity=data['package_quantity'],
                c_package_measurement=data['c_package_measurement'],
                measured_qty=data['measured_qty'],
                measured_unit=data['measured_unit'],
                barcode=data['barcode'],
                rack_code=r_code,
                item_name=data['item_name'],
                mrp=data['mrp'],
                price_with_tax=data['price_with_tax'],
                franchiser_isvid=data['franchiser_isvid'],
                measured_meaid=data['measured_meaid'],
                dealer_price=data['dealer_price'],
                commission_rate=data['commission_rate'],
                variance_percentage=data['variance_percentage'],
                package_meaid=data['package_meaid'],
                incentive=data['incentive'],
                cess=data['cess'],
                profitability=data['profitability'],
                shelf_life=data['shelf_life'],
                material_type=data['material_type'],
                is_price_fixed=data['is_price_fixed'],
                is_physical_count=data['is_physical_count'],
                physical_count_meaid=data['physical_count_meaid'],
                physical_count_qty=data['physical_count_qty'],
                physical_count_measurement=data['physical_count_measurement'],
                physical_meaid=data['physical_meaid'],
                stock_availability=data['stock_availability'],
                meatid=data['meatid'],
                purchase_discount=data['purchase_discount'],
                purchase_discount_type=data['purchase_discount_type'],
                sales_discount=data['sales_discount'],
                sales_discount_type=data['sales_discount_type'],
                appltid=data['appltid'],
                secondary_tax=data['secondary_tax'],
                price_limit=data['price_limit'],
                if_customization=data['if_customization'],
                default_base=data['default_base'],
                default_price_base=data['default_price_base'],
                franchise_commission=data['franchise_commission'],
                franchise_price=data['franchise_price'],
                franchise_selling_price=data['franchise_selling_price'],
                image=data['image'],
                limit=data['limit'],
            )

        return  productinerp_instance


class ErpUserSerailzier(serializers.ModelSerializer):
    

    class Meta:
        model = ERPUser
        fields = '__all__'
    
    def create(self, validated_data):
        response_API = requests.get('http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=quotation%2Fquotation_search_customer&user_id=410002661&access_token=6706619512258332164&search=a&balance=1')
            # print(type(response_API))
        records = response_API.text
        records = json.loads(records)
        records = records['data']
        records = records['customerList']
        print(records)

        for data in records:
                print(data)

                # v_code = None
                # if data['vendor_code'] != '' and data['vendor_code'] != ' ' :
                #     v_code = data['vendor_code']
                
                # r_code = None
                # if data['rack_code'] != '' and data['rack_code'] != ' ' :
                #     v_code = data['rack_code']
                
                productinerp_instance = ERPUser.objects.create(
                    erp_id=data['id'],
                    user_id=data['user_id'],
                    user_name=data['user_name'],
                    city=data['city'],
                    customer_number=data['customer_number'],
                    name=data['name'],
                    #mobile=data['mobile'],
                    email=data['email'],
                    #ctype=data['ctype'],
                    company_name=data['company_name'],
                    markup=data['markup'],
                    pan=data['pan'],
                    gstin=data['gstin'],
                    is_branch=data['is_branch'],
                    alid=data['alid'],
                    custid=data['custid'],
                    cutid=data['cutid'],
                    is_export=data['is_export'],
                    venid=data['venid'],
                    venid_alid=data['venid_alid'],
                    special_discount=data['special_discount'],
                    customer_type=data['customer_type'],
                    transaction_type=data['transaction_type'],
                    cash_bank=data['cash_bank'],
                    payment_terms=data['payment_terms'],
                    payment_day=data['payment_day'],
                    tcs=data['tcs'],
                    display_name=data['display_name'],
                )
                
        return  'productinerp_instance'