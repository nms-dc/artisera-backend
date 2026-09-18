
from datetime import date, timedelta, datetime
from django.utils import timezone

import json
import requests
import boto3
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
import copy
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from django.http import HttpResponse, JsonResponse
from accounts.models import Address, User, create_username, DailyVisit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from accounts.api.serializers import UserRegistrationSerializer, UserBasicInfoSerializer, UserProfileInfoSerializer, DailyVisitsSerializer
from rest_framework import viewsets
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
import secrets
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from twilio.rest import Client


def daily_visit_count():
    today = date.today()
    visit, created = DailyVisit.objects.get_or_create(date=today)
    visit.count += 1
    visit.save()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 10000


@csrf_exempt
def logout_View(request):
    logout(request)
    return HttpResponse("logout successful")


@api_view(['post', ])
@csrf_exempt
@permission_classes([AllowAny])
@authentication_classes([])
def user_login_view(request):

    if request.method == 'POST':
        data = request.data
        user_data = {}
        if 'email' in data or 'password' in data:
            user = authenticate(request, email=data['email'], password=data['password'])
            if user is not None:
                login(request, user)
                user_data = UserBasicInfoSerializer(instance=user).data
                # data['token']=token
                id = user_data['id']
                token = Token.objects.get(user=id).key
                print(token)
                daily_visit_count()
                return Response(user_data)
            else:
                user_data['message'] = "login failed"
                return Response(user_data, status=status.HTTP_401_UNAUTHORIZED)
        elif 'phone' in data and 'otp' in data:
            phone_number = data['phone']
            entered_otp = data['otp']
            
            user = authenticate(request, phone_no=phone_number, otp=entered_otp)
            
            if user is not None:
                login(request, user)
                user_data = UserBasicInfoSerializer(instance=user).data
                id = user_data['id']
                token = Token.objects.get(user=id).key
                print(token)
                daily_visit_count()
                return Response(user_data)
            else:
                user_data['message'] = "invalid otp or phone number"
                return Response(user_data, status=status.HTTP_401_UNAUTHORIZED)
        else:
            user_data['message'] = "invalid otp or phone number"
            return Response(user_data, status=status.HTTP_400_BAD_REQUEST)
    else:
        user_data['message'] = "please log in through admin account"
        return Response(user_data, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'POST', 'PATCH'])
@csrf_exempt
def user_registration_view(request, user_id=None):
    pagination_class = StandardResultsSetPagination
    if request.method == 'POST':
        serialize = UserRegistrationSerializer(data=request.data)
        data = {}
        if serialize.is_valid():
            user = serialize.save()
            daily_visit_count()
            data['response'] = "Successfully registered a new user."
            data['id'] = user.id
            data['email'] = user.email
            data['phone_no'] = user.phone_no
            data['first_name'] = user.first_name
            data['last_name'] = user.last_name
            data['username'] = user.username
            data['is_verified'] = user.is_verified
            data['is_admin'] = user.is_admin
            data['is_terms_accepted'] = user.is_terms_accepted
            token = Token.objects.get(user=user).key
            data['token'] = token
        else:
            data = serialize.errors
        return Response(data)

    elif request.method == 'GET':
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                serialized_user = UserRegistrationSerializer(user).data
                return Response(serialized_user)
            except User.DoesNotExist:
                return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            data = User.objects.all()
            re = UserRegistrationSerializer(data, many=True).data
            return Response(re)

    elif request.method == 'PATCH':
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                serialize = UserRegistrationSerializer(user, data=request.data, partial=True)
                data = {}
                if serialize.is_valid():
                    user = serialize.save()
                    data['response'] = "User details updated Successfully"
                    data['id'] = user.id
                    data['email'] = user.email
                    data['phone_no'] = user.phone_no
                    data['first_name'] = user.first_name
                    data['last_name'] = user.last_name
                    data['username'] = user.username
                    data['is_verified'] = user.is_verified
                    data['is_terms_accepted'] = user.is_terms_accepted
                    data['is_admin'] = user.is_admin
                    return Response(data)
                else:
                    return Response(serialize.errors, status=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"message": "User ID not provided"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['post', 'get'])
@csrf_exempt
def user_terms_accept(request):

    if request.method == 'POST':

        dic = request.data
        mail = dic['email']
        filtering = User.objects.filter(email=mail)
        filtering.update(is_term_accepted = True)
        user = UserRegistrationSerializer(filtering, many=True).data
        return Response(user)
    elif request.method == 'GET':
        data = User.objects.all()
        serialize = UserRegistrationSerializer(data, many=True).data
        print(request)
        return Response(serialize)


class user_profile_view(viewsets.ModelViewSet):

    queryset = User.objects.all()
    serializer_class = UserProfileInfoSerializer
    #authentication_classes = []
    #permission_classes = [IsAuthenticated]
    #http_method_names = ['post', 'get', 'patch', 'retrieve', 'put']
    pagination_class = StandardResultsSetPagination


class Forgot_pin(viewsets.ModelViewSet):
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()
    pagination_class = StandardResultsSetPagination


@api_view(['post', 'get'])
@csrf_exempt
def validate_email(request):

    if request.method == 'POST':
        dic = request.data
        mail = dic['email']
        filtering = User.objects.filter(email=mail)
        print(mail, filtering)
        if filtering:
            return Response('validating in progress')
        else:
            return Response('no email found')
    else:
        return Response('get operation cannot be performed')


@api_view(['post', 'get'])
@csrf_exempt
def change_password(request):

    if request.method == 'POST':
        dic = request.data
        mail = dic['email']
        user = User.objects.get(email=mail)
        passwd1 = dic['password1']
        passwd2 = dic['password2']
        if passwd1 == passwd2:
            user.set_password(dic['password1'])
            user.save()
            return Response('password changed successfully')
    else:
        return Response('get operation cannot be performed')


class DailyVisitsView(APIView):
    def get(self, request):
        try:
            visit = DailyVisit.objects.get(date=date.today())
            serializer = DailyVisitsSerializer(visit)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DailyVisit.DoesNotExist:
            return Response({"count": 0}, status=status.HTTP_200_OK)


# Function to generate a random 6-digit OTP securely
def generate_random_otp():
    otp_length = 6
    otp = ''.join([str(secrets.randbelow(10)) for _ in range(otp_length)])
    return otp

# View for sending OTP


@csrf_exempt
def send_otp(request):
# Create an SNS client
    client = boto3.client(
        "sns",
        aws_access_key_id="XXXXXXXXXXXXX",
        aws_secret_access_key="XXXXXXXXXXXXXXXX",
        region_name="ap-south-1"
    )
    if request.method == "POST":
        phone = request.POST.get("phone")
        otp = generate_random_otp()
        creation_time = datetime.now()
        try:
            user = User.objects.get(phone_no=phone)
        except User.DoesNotExist:
            return JsonResponse({"success": False, "message": "User does not exist"})

        try:
            response = client.publish(
                PhoneNumber=f"+91{phone}",
                Message=f"{otp} is the verification code to log in to your chabsons account, Don't share it with anyone.",
            )  

            cache_key = f"otp_{phone}"
            creation_time = datetime.now()
            cache.set(cache_key, (otp, creation_time), 300)

            return JsonResponse({"success": True, "first_name": user.first_name, 'phone': phone})
        except Exception as e:
            print("Error sending OTP:", str(e))
            return JsonResponse({"success": False})


def verify_otp(phone_number, entered_otp):
    try:
        otp_data = cache.get(f"otp_{phone_number}")
        if otp_data is not None:
            stored_otp, creation_time = otp_data
            if (
                stored_otp == entered_otp
                and datetime.now() <= creation_time + timedelta(minutes=5)
            ):
                cache.delete(f"otp_{phone_number}")
                return True
        else:
            return False
    except ObjectDoesNotExist:
        return False

# from django.http import JsonResponse

# @api_view(['get'])
# @csrf_exempt
# def customer_inserter(request):
#     # Send an HTTP GET request to the external API
#     api_url ='http://chhabriasons.sixorbit.com//?urlq=service&version=4.0&key=123&task=customer%2Ffetch&user_id=410002661&access_token=6613527815757554180&last_fetch&traversal&search&order_flag&start_limit&cno'
#     try:
#         response = requests.get(api_url)
#         response.raise_for_status()  # Check for any HTTP request errors
#         api_data = response.json()

#         # Extract the 'customers' data from the API response
#         customers = api_data['data']['customers']

#         for customer_data in customers:
#             try:
#                 created_at_str = customer_data['created_ts']
#                 created_at = timezone.make_aware(datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S"), timezone=timezone.utc)
#                 updated_at_str = customer_data['updated_ts']
#                 updated_at = timezone.make_aware(datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S"), timezone=timezone.utc)


#                 # Map API data to User model fields and create a new user instance
#                 user_instance = User.objects.create(
#                     cuid=customer_data['cuid'],
#                     alid=customer_data['alid'],
#                     customer_number=customer_data['customer_number'],
#                     first_name=customer_data['cust_name'],  # Adjust this mapping as needed
#                     last_name=customer_data['lname'],  # Adjust this mapping as needed
#                     email=customer_data['email'],
#                     phone_no=customer_data['mobile'],
#                     company_name=customer_data['company_name'],
#                     sic_gst_code=customer_data['gstin'],  # Adjust this mapping as needed
#                     address_one=customer_data['address'],
#                     created_at=created_at,
#                     updated_at=updated_at,
#                     wallet_balance=customer_data['wallet_balance']
#                 )

#                 # Optionally, you can create an Address instance as well
#                 # Make sure to define the Address model in your app
#                 # address_instance = Address.objects.create(address_one=customer_data['address'])

#             except Exception as e:
#                 print(f"Error inserting customer: {e}")

#         return JsonResponse(customers, safe=False)  # Return the inserted data as a JSON response

#     except requests.exceptions.RequestException as e:
#         print(f"API request failed: {e}")
#         return JsonResponse({"error": "API request failed"}, status=500)

#     except json.JSONDecodeError as e:
#         print(f"Error decoding API response: {e}")
#         return JsonResponse({"error": "API response decoding failed"}, status=500)


@api_view(['get'])
@csrf_exempt
def customer_inserter(request):
    last_fetch = request.query_params.get('last_fetch', None)
    if last_fetch:
        responses = requests.get(
            f'http://chhabriasons.sixorbit.com//?urlq=service&version=4.0&key=123&task=customer%2Ffetch&user_id=410002661&access_token=6613527815757554180&last_fetch={last_fetch}&traversal&search&order_flag&start_limit&cno&default_limit=250')
    else:
        responses = requests.get(
            f'http://chhabriasons.sixorbit.com//?urlq=service&version=4.0&key=123&task=customer%2Ffetch&user_id=410002661&access_token=6613527815757554180&traversal&search&order_flag&start_limit&cno&default_limit=250')

    datas = json.loads(responses.text)
    customers = datas['data']['customers']
    for customer in customers:
        try:
            mobile_data = customer['mobile'].replace(" ", "")
            mobile_numbers = mobile_data.split('/')
            phone = mobile_numbers[0]

            if User.objects.filter(email=customer['email']).exists() or User.objects.filter(phone_no=phone).exists():
                continue

            user_instance = User.objects.create(
                email=customer['email'],
                first_name=customer['fname'],
                last_name=customer['lname'],
                phone_no=phone,
                isErpCustomer = True 
            )

            if customer['email'].lower() == "no@gmail.com":
                user_instance.email = f'null{user_instance.id}@gmail.com'

            created_at_str = customer['created_ts']
            created_at = timezone.make_aware(datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S"), timezone=timezone.utc)
            updated_at_str = customer['updated_ts']
            updated_at = timezone.make_aware(datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S"), timezone=timezone.utc)

            user_instance.cuid = customer.get('cuid', '')
            user_instance.alid = customer.get('alid', '' )
            user_instance.customer_number = customer.get('customer_number', '')
            user_instance.company_name = customer.get('company_name', '')
            user_instance.sic_gst_code = customer.get('gstin', '')  # Use .get() to handle missing keys
            user_instance.address_one = customer.get('address', '')
            user_instance.created_at = created_at
            user_instance.updated_at = updated_at
            user_instance.wallet_balance = customer.get('wallet_balance', '')
            user_instance.is_verified = True

            user_instance.save()

        except Exception as e:
            print(f"Error inserting customer: {e}")

        # adding address from erp

        # try:
        #     address_instance = Address.objects.create(
        #         address_one = customer['address'],
        #     )
        # except Exception as e:
        #     print(f"Error inserting address: {e}")

    return Response(customers, content_type='json/application')


{
    "uid": "410000275", #mandatory
    "baid": "410997421", #mandatory
    "said": "410997421",  #mandatory
    "cc": "",
    "cuid": "410907842",
    "dealer_price": "1", #not mandatory
    "chkid": "410000351", #not mandatory
    "etid": "", 
    "ortemid": "410000060", #not mandatory
    "smstid": "",
    "discount": "10",
    "discount_type": "1", #not mandatory
    "mail": "0",
    "sms": "0",
    "attributes": "",
    "checkpoint_order_remarks": "Test order",
    "round": "0.19", #not mandatory
    "round_field": "0", #not mandatory
    "payment-terms": 1, #mandatory
    "category_type": "1", #not mandatory
    "price_variation_id_main": "19", #not mandatory
    "day": "",
    "advance_payment": "1", #not mandatory
    "payment_mode": "3", #not mandatory
    "payment": "410205189", #not mandatory
    "advance_amount": "10", #not mandatory
    "payment_attrs": "",  #not mandatory
    "custid": "1", #not mandatory
    "alid": "",
    "order_type": "1", # mandatory
    "percent-limit": "", #not mandatory
    "order_no": "QCSW", 
    "date": "06-01-2022",
    "due_date": "07-01-2022", #not mandatory
    "delivery_date": "15-10-2023",
    "create_date": "12-10-2023", #not mandatory
    "shipping_type": "2", #not mandatory
    "trid": "28", #not mandatory
    "t_name": "Priya Gupta", #not mandatory
    "cart": [
        {
            "iitid": "1", #not mandatory
            "isvid": "17170",
            "iid": "410425038", #not mandatory
            "name": "OYD10299 A SP1 - PENDENT LAMP (ANTIQUE)",
            "meaid": "40", #not mandatory
            "price_meaid": "40", #not mandatory
            "quantity": "1",
            "price": "10620.00",
            "dealer_price": "null", #not mandatory
            "amount": "10620.0",
            "measurements": "Box", #uom
            "price_conversion_rate": "1.00000000", #not mandatory
            "conversion_rate": "1.00000000", #not mandatory
            "box_conversion_rate": "1", #not mandatory
            "box_qty": "1", #not mandatory
            "image": "http://demolive.sixorbit.com/rpkfiles/variations/small_thumbnail/544d68f6ebaddf82b890505799009dbd1749203f.jpg",
            "discount": "0.00",
            "discount_type": "1",
            "product_attributes": "",
            "description": "",
            "type": "1",
            "roundoff": "0",
            "item_service": "0",
            "price_unit_conversion_rate": "1.0",
            "quantity_unit_conversion_rate": "1.0",
            "remark": "",
            "price_variation_id_item": "19"
        }
    ],
    "pre_charge": [
        {
            "id": "410000341",
            "value": "10.00",
            "charges": "410001348"
        },
        {
            "id": "410000572",
            "value": "0",
            "charges": "0"
        },
        {
            "id": "410000664",
            "value": "0.00",
            "charges": "410001348"
        }
    ],
    "material_tax": "",
    "post_charge": [
        {
            "id": "410000397",
            "value": "0"
        }
    ],
    "extra_discount": [
        {
            "id": "29000009",
            "type": "1",
            "discount": "10"
        }
    ],
    "bit": "1",
    "charge": [],
    "charges": ""
}
