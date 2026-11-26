import hashlib
from rest_framework.throttling import SimpleRateThrottle


class ChangePasswordIPThrottle(SimpleRateThrottle):
    scope = "change_password_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ChangePasswordEmailThrottle(SimpleRateThrottle):
    scope = "change_password_email"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "")).strip().lower()
        if not email:
            return None  # IP throttle still applies
        digest = hashlib.sha256(email.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
