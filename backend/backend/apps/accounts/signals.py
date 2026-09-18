# import json
# from django.db.models.signals import post_save, pre_delete
# from django.dispatch import receiver
# from .models import Address, User
# import requests

# @receiver(post_save, sender=User)
# def create_customer_data_and_send_to_api(sender, instance, created, **kwargs):
#     if not instance.isErpCustomer:
#         if created:
            
#             data = {
#                 "customer-type-radio": "2",
#                 "email": instance.email,
#                 "fname": instance.first_name,
#                 "lname": instance.last_name,
#                 "mobile": instance.phone_no,
#                 "current-line1": instance.address_one if instance.address_one else f'current-line1 not available',
#                 "current-line2": instance.address_two if instance.address_two else f'current-line2 not available',
#                 "current-pincode": instance.pincode if instance.pincode else "123456",
#                 "gender": "1",
#                 "form27C_checkBox": "0",
#             }

#             data_string = json.dumps(data)
#             payload = {"data": data_string}
#             print(payload)

#             api_url = "http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=customer/add_customer&user_id=410002591&access_token=6706067010728877060"  
            
#             response = requests.post(api_url, data=payload)

#             if response.status_code == 200:
#                 print("Request was successful")
#                 api_response = response.json()
#                 print(api_response)
#                 cuid = api_response.get("data", {}).get("cuid")     
#                 print("extracted cuid--> ", cuid)
#                 if cuid:
#                     instance.cuid = cuid
#                     instance.save()     
#             else:
#                 print(f"Request failed with status code: {response.status_code}")
#                 print("Response content:")
#                 print(response.content)

# @receiver(post_save, sender=Address)
# def send_get_request_to_add_address(sender, instance, created, **kwargs):
#     if created:
#         cuid = instance.user.cuid
#         add1 ='some address'
#         add2 ='some address 2'
#         addctid = '1'
#         addstid='304'
#         addcoverid ='410471512'
#         pincode ='560078'
#         fname ='Test%201'
#         lname ='Test'
#         mobile ='1253698254'

#         api_url = f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=customer%2Fadd_customer_address&user_id=410002591&access_token=6706067010728877060&cuid={cuid}&current-line1={add1}&current-line2={add2}&current-area=&current-ctid={addctid}&current-stid={addstid}&current-coverid={addcoverid}&current-pincode={pincode}&current-add-fname={fname}&current-add-lname={lname}&current-add-mobile={mobile}&current-add-sitename=&current-satid='

#         response = requests.get(api_url)
#         try:
#             response_data = response.json()
#             said = response_data['data']['said']
            
#             print("the said is ---> ", said)
#             instance.addsaid = said
#             instance.save()
#         except ValueError:
#             print("Failed to parse the response as JSON.")
#     else:
#         cuid = instance.user.cuid
#         add1 ='some address'
#         add2 ='some address 2'
#         addctid = '1'
#         addstid='304'
#         addsaid = '410997649'
#         addcoverid ='410471512'
#         pincode ='560078'
#         fname ='Test%201'
#         lname ='Test'
#         mobile ='1253698254'

#         api_url= f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=customer%2Fedit_address_submit&user_id=410002591&access_token=6706067010728877060&said={addsaid}&cuid={cuid}&current-line1={add1}&current-line2={add2}&current-ctid={addctid}&current-stid={addstid}&current-coverid={addcoverid}&current-pincode={pincode}&current-add-fname={fname}&current-add-lname={lname}&current-add-mobile={mobile}&current-add-sitename=&current-satid='

#         response = requests.get(api_url)
#         try:
#             response_data = response.json()
#             print(response_data)
#         except ValueError:
#             print("Failed to parse the response as JSON.")

# #to handle the deletion of model
# @receiver(pre_delete, sender=Address)
# def send_get_request_to_delete_address(sender, instance, **kwargs):

#     said = instance.said  # Get the 'said' value from the instance if this needs to be sent to the address api

#     #example api, edit this acc. to erp
#     api_url = f'http://chhabriasons.sixorbit.com/?urlq=service&version=4.0&key=123&task=customer%2Fdelete_customer_address&user_id=410002591&access_token=6706067010728877060&cuid={cuid}&current-satid={said}'

#     response = requests.get(api_url)

#     try:
#         response_data = response.json()
#         # You can handle the response or logging here if needed.
#         print(response_data)
#     except ValueError:
#         print("Failed to parse the response as JSON.")