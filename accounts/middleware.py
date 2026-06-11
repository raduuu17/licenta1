from django.shortcuts import redirect
from django.urls import reverse


class AdminTwoFactorMiddleware:
    """
    Enforce two-factor authentication (TOTP) for staff areas.

    After a staff user logs in with username/password, any access to the
    Django admin (/admin/) or the staff frontend (/staff/) requires OTP
    verification for the current session. Users without an enrolled device
    are sent to the setup page to scan the QR code.
    """

    PROTECTED_PREFIXES = ('/admin/', '/staff/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._requires_otp(request):
            from django_otp.plugins.otp_totp.models import TOTPDevice

            has_device = TOTPDevice.objects.filter(
                user=request.user, confirmed=True
            ).exists()
            target = 'two_factor_verify' if has_device else 'two_factor_setup'
            return redirect(f"{reverse(target)}?next={request.path}")

        return self.get_response(request)

    def _requires_otp(self, request):
        if not request.path.startswith(self.PROTECTED_PREFIXES):
            return False

        # The login/logout pages must stay reachable without OTP
        if request.path.startswith(('/admin/login', '/admin/logout')):
            return False

        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return False

        # is_verified() is added by django_otp.middleware.OTPMiddleware
        return not user.is_verified()
