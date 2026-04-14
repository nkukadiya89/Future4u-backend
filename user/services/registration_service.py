from email_utils.send_email import send_mail
from utils.generate_otp import generate_otp


def send_verify_email(user_email, user_name):
    # debug.info(f"Sending password reset email to {user_email}")
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
    # Placeholder for email sending logic
    user_email = user.email  # type: ignore
    user_name = user.first_name  # type: ignore
    otp = send_verify_email(user_email, user_name)  # type: ignore
    user.otp = otp
    user.save()  # type: ignore
