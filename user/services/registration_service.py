from django.utils import timezone

from email_utils.send_email import send_mail
from utils.auth import generate_temporary_password
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


def send_temporary_password_email(user, temporary_password):
    send_mail(
        "Your Future4U Temporary Password",
        "temporary-password.html",
        {
            "name": user.first_name,
            "email": user.email,
            "temporary_password": temporary_password,
        },
    )


def activate_web_user_with_temporary_password(user, *, send_email=True):
    temporary_password = generate_temporary_password()
    user.set_password(temporary_password)
    user.must_change_password = True
    user.email_verified = True
    user.is_active = True
    user.status = "active"
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
        send_temporary_password_email(user, temporary_password)
    return user
