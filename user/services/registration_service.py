from django.utils import timezone
from email_utils.send_email import send_mail
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
    user.save()
