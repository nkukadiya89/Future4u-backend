try:
    from celery import shared_task
except Exception:  # pragma: no cover - optional local dependency
    def shared_task(*args, **kwargs):
        def decorator(func):
            func.delay = func
            return func

        return decorator

from email_utils.send_email import generate_forget_pass_token, send_mail
from user.models import User


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_company_reset_password_email_task(self, user_id: int):
    user = User.objects.get(id=user_id)
    token = generate_forget_pass_token(user.email, user.phone, 30)
    context = {
        "name": user.first_name,
        "email": user.email,
        "token": token,
    }
    send_mail("Reset Your Password", "reset-pass.html", context)
