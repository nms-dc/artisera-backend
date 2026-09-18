# import json
# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import  Transaction
# import requests

# @receiver(post_save, sender = Transaction)
# def create_order_data_and_send_to_api(sender , instance, created, **kwargs):
#     if created:
#       print("signal is entering  -----> ")
#       print(instance)
#       data = {
#           "order_number" : instance.order_summary.order_number,
#           "user_data" : {
#               "user_name" : f'{instance.order_summary.user.first_name} {instance.order_summary.user.last_name}',
#               "user_email" : instance.order_summary.user.email
#           },
#           "order_status" : instance.order_summary.order_status,
#           #assuming this address data is saved in ordersummay model
#           "address":{
#               "address_one" : instance.order_summary.address_one,
#               "address_two" : instance.order_summary.address_two,
#               "pincode" : instance.order_summary.pincode,
#               "city" : instance.order_summary.city,
#               "state" : instance.order_summary.state
#           },
#           "transaction_details" :{
#               "mihpayid": instance.mihpayid,
#               "txnid": instance.txnid,
#               "addedon": instance.addedon,
#               "bank_ref_num": instance.bank_ref_num,
#           },
          
#       }

#       # example of how we will handle/create n number of products or anything else inside an arry or objects
#       cart = []
#       for order_detail in instance.order_summary.order_details.all():
#           product_data = {
#               "quantity": order_detail.quantity,
#               "price": order_detail.price,
#               "product": order_detail.product.id
#           }
#           cart.append(product_data)

#       data["cart"] = cart

#       # Convert the data to JSON
#       data_string = json.dumps(data)
#       payload = {"data": data_string}

#       print(payload)

#       # Make a POST request to the desired URL

#       # api_url = "http://your-api-endpoint-here"
#       # response = requests.post(api_url, data=payload, headers={'Content-Type': 'application/json'})

#       # if response.status_code == 200:
#       #     # Handle a successful response
#       #     print("POST request successful.")
#       # else:
#       #     # Handle errors here
#       #     print(f"POST request failed with status code: {response.status_code}")


