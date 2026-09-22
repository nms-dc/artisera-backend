from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from common.tasks import mock_slow_task, send_email_mockup


class TriggerTaskView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        name = request.data.get('name', 'anonymous')
        email = request.data.get("email", "sample@gmail.com")
        result = mock_slow_task.delay(name)
        result1 = send_email_mockup.delay(email)
        return Response({'task_ids': [result.id,result1.id], 'status': 'queued'})