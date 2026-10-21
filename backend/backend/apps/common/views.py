from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
# common/views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.tasks import mock_slow_task, send_email_mockup


class TriggerTaskView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name', 'anonymous')
        email = request.data.get("email", "sample@gmail.com")
        result = mock_slow_task.delay(name)
        result1 = send_email_mockup.delay(email)
        return Response({'task_ids': [result.id,result1], 'status': 'queued'})




REQUIRED = ["customer_id", "inquiry_type", "product_requirement", "quantity", "inquiry_value"]

@csrf_exempt
@require_POST
def create_inquiry(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    missing = [f for f in REQUIRED if f not in data]
    if missing:
        return JsonResponse({"error": f"Missing fields: {missing}"}, status=400)

    is_admin = request.headers.get("X-Role") == "admin"  # mock role check

    inquiry = {
        "id": 1,  # mock
        "customer_id": data["customer_id"],
        "inquiry_type": data["inquiry_type"],
        "product_requirement": data["product_requirement"],
        "quantity": data["quantity"],
        "inquiry_value": data["inquiry_value"],
        "category": data.get("category"),
        "subcategory": data.get("subcategory"),
        "artist": data.get("artist"),
        "initial_notes": data.get("initial_notes", ""),
        # Admin only
        "rm_id": data.get("rm_id") if is_admin else None,
        "priority": data.get("priority", "medium") if is_admin else "medium",
    }
    return JsonResponse(inquiry, status=201)