from rest_framework_simplejwt.authentication import JWTAuthentication
from decouple import config


class JWTAndWebhookAuthentication(JWTAuthentication):
    """
    Backward-compatible authentication class used in settings.
    """

    def authenticate(self, request):
        # Keep existing JWT auth behavior.
        user_auth_tuple = super().authenticate(request)
        if user_auth_tuple is not None:
            return user_auth_tuple

        # Optional lightweight webhook auth fallback.
        webhook_token = request.headers.get("X-Webhook-Token")
        expected_token = config("WEBHOOK_TOKEN", default="")

        if webhook_token and expected_token and webhook_token == expected_token:
            # Webhook endpoints may still define AllowAny permissions.
            return None

        return None

    def authenticate_header(self, request):
        return "Bearer"
