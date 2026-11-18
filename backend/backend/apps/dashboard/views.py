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
    """
    GET /api/v1/crm/dashboard/rm/

    - RM:    no parameters needed; always returns the logged-in RM's dashboard
             (any rmId in the query string is ignored).
    - Admin: rmId is optional. With rmId, returns that RM's dashboard;
             without it, returns the Admin's own dashboard (no 400).
    - range: optional number of days (default 30).
    """

    permission_classes = [IsAdminOrRM]

    def get(self, request):
        try:
            range_days = int(request.query_params.get("range", 30))
        except (TypeError, ValueError):
            range_days = 30

        rm = request.user

        # Only an Admin may look at another RM's dashboard.
        if request.user.is_admin:
            rm_id = request.query_params.get("rmId")

            if rm_id:
                try:
                    rm = User.objects.get(
                        id=rm_id,
                        is_active=True,
                        role_id=RM_ROLE_ID,
                    )
                except (User.DoesNotExist, ValueError, ValidationError):
                    return Response(
                        {"rmId": ["RM not found."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        data = get_rm_dashboard(rm=rm, range_days=range_days)
        return Response(data)
