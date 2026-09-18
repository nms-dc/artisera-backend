from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .api.views import verify_otp

User = get_user_model()

class PhoneOTPBackend(ModelBackend):
    def authenticate(self, request, phone_no=None, otp=None, **kwargs):
        if phone_no is not None and otp is not None:
            if verify_otp(phone_no, otp):
                try:
                    user = User.objects.get(phone_no=phone_no)
                    return user if user else None
                except User.DoesNotExist:
                    return None
            else:
                return None
        return None
