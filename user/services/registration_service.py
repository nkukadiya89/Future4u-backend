from django.utils import timezone

from email_utils.send_email import (
    WEB_PASSWORD_SETUP_TOKEN_DAYS,
    generate_token,
    send_mail,
)
from utils.generate_otp import generate_otp


def send_verify_email(user_email, user_name):
    subject = "Verify Your Email for Future4u"
    otp = generate_otp()
    context = {
        "email": user_email,
        "name": user_name,
        "otp": otp,
    }
    send_mail(subject, "register-success.html", context)
    return otp


def send_registration_email(user):
    user_email = user.email
    user_name = user.first_name
    otp = send_verify_email(user_email, user_name)
    user.otp = otp
    user.otp_created_at = timezone.now()
    user.save(update_fields=["otp", "otp_created_at"])


def setup_web_user_password(user, *, send_email=True):
    from user.tasks import send_password_setup_link_task

    user.set_unusable_password()
    user.must_change_password = True
    user.email_verified = False
    user.is_active = False
    user.status = "pending"
    user.otp = None
    user.otp_created_at = None
    user.save(
        update_fields=[
            "password",
            "must_change_password",
            "email_verified",
            "is_active",
            "status",
            "otp",
            "otp_created_at",
        ]
    )
    if send_email:
        token = generate_token(user.email, WEB_PASSWORD_SETUP_TOKEN_DAYS)
        send_password_setup_link_task.delay(
            user.first_name,
            user.email,
            token,
        )
    return user
