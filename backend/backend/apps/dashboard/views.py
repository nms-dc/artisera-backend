from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from accounts.models import User, RM_ROLE_ID
from .permissions import IsAdminUser
from .services import (
    get_admin_dashboard,
    get_rm_dashboard,
)
from .permissions import (
    IsAdminUser,
    IsAdminOrRM,
)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            range_days = int(request.query_params.get("range", 30))
        except ValueError:
            range_days = 30

        data = get_admin_dashboard(range_days=range_days)
        return Response(data)


class RMDashboardView(APIView):
    permission_classes = [IsAdminOrRM]

    def get(self, request):
        try:
            range_days = int(
                request.query_params.get("range", 30)
            )
        except ValueError:
            range_days = 30

        rm_id = request.query_params.get("rmId")

        # ==============================================
        # ADMIN
        # Admin must explicitly select an RM
        # ==============================================
        if request.user.is_admin:

            if not rm_id:
                return Response(
                    {
                        "rmId": [
                            "This field is required for Admin."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                rm = User.objects.get(
                    id=rm_id,
                    is_active=True,
                    role_id=RM_ROLE_ID,
                )
            except User.DoesNotExist:
                return Response(
                    {
                        "rmId": [
                            "RM not found."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ==============================================
        # NORMAL RM
        # rmId is ignored; user sees own dashboard
        # ==============================================
        else:
            rm = request.user

        data = get_rm_dashboard(
            rm=rm,
            range_days=range_days,
        )

        return Response(data)