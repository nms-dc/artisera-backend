from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import (
    CurrentUserSerializer,
    UserOptionSerializer,
    UserListSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    RoleOptionSerializer,
    RoleListSerializer,
    RoleCreateSerializer,
    RoleUpdateSerializer,
)
from accounts.models import User, Role
from django.core.paginator import Paginator
from django.db.models import Q
import requests
from rest_framework.exceptions import Throttled

from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny

from .serializers import ChangePasswordSerializer
from .throttles import ChangePasswordIPThrottle, ChangePasswordEmailThrottle

# Hashed once at import; used to keep timing equal when the email is unknown.
_DUMMY_HASH = make_password("dummy-password-for-timing")

INVALID_CREDENTIALS = {"detail": "Invalid email or current password."}


def _invalidate_sessions(user):
    """Revoke every credential the user currently holds."""
    # DRF TokenAuthentication
    Token.objects.filter(user=user).delete()

    # Django sessions
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
            session.delete()

    # SimpleJWT refresh tokens (only if the blacklist app is installed)
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
    except ImportError:
        pass


class LogoutView(APIView):
    """
    POST /api/v1/account/auth/logout/
    Payload: {} (none)    Response: {}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # --- A) DRF TokenAuthentication: delete the token server-side ---
        if request.auth is not None and hasattr(request.auth, "delete"):
            request.auth.delete()

        # --- B) SessionAuthentication: clear the session ---
        django_logout(request)

        return Response({}, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class UserOptionsView(ListAPIView):
    serializer_class = UserOptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.filter(is_active=True)

        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role_id=role)

        return queryset.order_by("name")

    def post(self, request):
        if not request.user.can("users", "create"):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        return Response(
            UserListSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.can("users", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        queryset = User.objects.select_related("role").all()

        search = request.query_params.get("q")
        role = request.query_params.get("role")
        status_filter = request.query_params.get("status")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        if role:
            queryset = queryset.filter(role_id=role)

        if status_filter:
            queryset = queryset.filter(is_active=(status_filter.lower() == "active"))

        queryset = queryset.order_by("name")

        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = max(int(request.query_params.get("pageSize", 10)), 1)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = UserListSerializer(page_obj.object_list, many=True)

        return Response(
            {
                "count": paginator.count,
                "page": page_obj.number,
                "pageSize": page_size,
                "results": serializer.data,
            }
        )

    def post(self, request):
        if not request.user.can("users", "create"):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user = User.objects.select_related("role").get(pk=user.pk)
        return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("users", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            user = User.objects.select_related("role").get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(UserListSerializer(user).data)

    def patch(self, request, pk):
        if not request.user.can("users", "edit"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            user = User.objects.select_related("role").get(pk=pk)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # A user cannot deactivate themselves.
        if (
            str(user.pk) == str(request.user.pk)
            and request.data.get("status") == "Inactive"
        ):
            return Response(
                {"status": ["You cannot deactivate yourself."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserUpdateSerializer(
            user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user.refresh_from_db()

        return Response(UserListSerializer(user).data)


class RoleOptionsView(ListAPIView):
    serializer_class = RoleOptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Role.objects.filter(status=Role.Status.ACTIVE).order_by("name")


class RoleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.can("users", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        queryset = Role.objects.all()

        search = request.query_params.get("q")
        status_filter = request.query_params.get("status")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        queryset = queryset.order_by("name")

        page = max(int(request.query_params.get("page", 1)), 1)
        page_size = max(int(request.query_params.get("pageSize", 10)), 1)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)

        serializer = RoleListSerializer(
            page_obj.object_list,
            many=True,
        )

        return Response(
            {
                "count": paginator.count,
                "page": page_obj.number,
                "pageSize": page_size,
                "results": serializer.data,
            }
        )

    def post(self, request):
        if not request.user.can("users", "create"):
            raise PermissionDenied("You do not have permission to do this.")

        serializer = RoleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        role = serializer.save()

        return Response(
            RoleListSerializer(role).data,
            status=status.HTTP_201_CREATED,
        )


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not request.user.can("users", "view"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response(
                {"detail": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(RoleListSerializer(role).data)

    def patch(self, request, pk):
        if not request.user.can("users", "edit"):
            raise PermissionDenied("You do not have permission to do this.")

        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response(
                {"detail": "Role not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RoleUpdateSerializer(
            role,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        role = serializer.save()

        return Response(RoleListSerializer(role).data)


class ChangePasswordView(APIView):
    """
    POST /api/v1/account/auth/change-password/
    Public endpoint. currentPassword in the body is the proof of identity.
    Works for new users (currentPassword = default password) and existing users.
    """

    authentication_classes = []  # public; also avoids CSRF/stale-token 401s
    permission_classes = [AllowAny]
    throttle_classes = [ChangePasswordIPThrottle, ChangePasswordEmailThrottle]

    def throttled(self, request, wait):
        raise Throttled(wait=wait, detail="Too many attempts. Try again later.")

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["email"].strip()
        current_password = data["currentPassword"]
        new_password = data["newPassword"]

        # --- Verify email + current password (active users only) ---
        user = User.objects.filter(email__iexact=email, is_active=True).first()

        if user is None:
            # Spend the same time as a real check, then return the generic error.
            from django.contrib.auth.hashers import check_password

            check_password(current_password, _DUMMY_HASH)
            return Response(INVALID_CREDENTIALS, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response(INVALID_CREDENTIALS, status=status.HTTP_400_BAD_REQUEST)

        # --- Standard Django validators (user-aware), after identity is proven ---
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"newPassword": list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --- Save ---
        with transaction.atomic():
            user.set_password(new_password)
            update_fields = ["password"]
            if hasattr(user, "must_change_password"):
                user.must_change_password = False
                update_fields.append("must_change_password")
            user.save(update_fields=update_fields)

            _invalidate_sessions(user)

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )
