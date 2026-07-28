import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jwt
from decouple import config
from django.conf import settings
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string

from utils.email_logger import log_email_failed, log_email_sent

WEB_PASSWORD_SETUP_TOKEN_DAYS = 1


def generate_token(email=None, token_time=None):
    exp_time = datetime.now() + timedelta(days=token_time)
    JWT_PAYLOAD = {
        "email": email,
        "exp": exp_time,
    }
    jwt_token = jwt.encode(JWT_PAYLOAD, config("SECRET_KEY"), algorithm="HS256")
    return jwt_token


def generate_forget_pass_token(email=None, user_phone=None, token_time=None):
    exp_time = datetime.now() + timedelta(days=token_time)
    JWT_PAYLOAD = {
        "email": email,
        "phone": user_phone,
        "exp": exp_time,
    }
    jwt_token = jwt.encode(JWT_PAYLOAD, config("SECRET_KEY"), algorithm="HS256")
    return jwt_token


def decode_token(token):
    payload = jwt.decode(token, config("SECRET_KEY"), algorithms="HS256")
    return payload


def pr_decode_token(token):
    try:
        payload = jwt.decode(token, config("SECRET_KEY"), algorithms="HS256")
        return payload

    except jwt.ExpiredSignatureError:
        return {"error": "Token signature has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}


def _get_app_url():
    return config(
        "APP_URL",
        default=getattr(settings, "FRONTEND_URL", "https://app.future4u.ai"),
    ).rstrip("/")


def _build_email_context(template, data):
    context = {"name": data["name"]}
    app_url = _get_app_url()
    if template == "register-success.html" or template == "verify_account.html":
        generate_token(data["email"], 30)
        context["login_url"] = app_url + "/login"
        context["verify_link"] = app_url + "/verify-success/"
        context["verification_code"] = data["otp"]
        context["email"] = data["email"]
    elif template == "reset-pass.html":
        context["path"] = app_url + "/reset-password/"
        token_value = data["token"]
        if isinstance(token_value, (bytes, bytearray)):
            token_value = token_value.decode("utf-8")
        context["token"] = str(token_value)
    elif template == "forgot-pass.html":
        context["path"] = app_url + "/forgot-password/"
        token_value = data["token"]
        if isinstance(token_value, (bytes, bytearray)):
            token_value = token_value.decode("utf-8")
        context["token"] = str(token_value)
    elif template == "set-password.html":
        context["path"] = app_url + "/reset-password/"
        token_value = data["token"]
        if isinstance(token_value, (bytes, bytearray)):
            token_value = token_value.decode("utf-8")
        context["token"] = str(token_value)
        context["email"] = data["email"]
    elif template == "temporary-password.html":
        context["temporary_password"] = data["temporary_password"]
        context["login_url"] = app_url + "login"
        context["email"] = data["email"]

    elif template == "bulk-upload-summary.html":
        context["total_records"] = data["total_records"]
        context["inserted"] = data["inserted"]
        context["failed"] = data["failed"]
        context["skipped"] = data["skipped"]
        context["errors"] = data.get("errors", [])
    elif template == "email-changed.html":
        context["email"] = data["email"]
        context["old_email"] = data["old_email"]
        context["new_email"] = data["new_email"]

    return context


def _build_email_message(subject, template, data, *, logo_bytes, checked_bytes=None):
    """
    Build a MIME message with inline CID images.

    Some clients (notably Gmail) require multipart/related with an HTML body
    inside multipart/alternative for CID images to render reliably.
    """
    html_body = render_to_string(template, _build_email_context(template, data))
    to_email = data["email"]

    # Root container: inline assets related to the HTML body
    msg = MIMEMultipart("related")
    msg.set_unixfrom("author")
    msg["From"] = "Future4U <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = to_email
    msg["Subject"] = subject

    # HTML body container (recommended for email clients)
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # Inline logo
    ms_image = MIMEImage(logo_bytes)
    ms_image.add_header("Content-ID", "<image1>")
    ms_image.add_header("Content-Disposition", "inline", filename="logo.png")
    msg.attach(ms_image)

    # Optional inline checkmark
    if template == "register-success.html" and checked_bytes:
        ms_image_checked = MIMEImage(checked_bytes)
        ms_image_checked.add_header("Content-ID", "<image2>")
        ms_image_checked.add_header(
            "Content-Disposition", "inline", filename="checked.png"
        )
        msg.attach(ms_image_checked)

    return msg, to_email


def _get_static_image_bytes(filename):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base_dir, "static/images", filename)
    with open(path, "rb") as image_file:
        return image_file.read()


def send_mail(subject, template, data):
    custom_message_content = None
    logo_bytes = _get_static_image_bytes("f4u-h-final.png")
    checked_bytes = None
    if template == "register-success.html":
        checked_bytes = _get_static_image_bytes("checked.png")

    msg, to_email = _build_email_message(
        subject,
        template,
        data,
        logo_bytes=logo_bytes,
        checked_bytes=checked_bytes,
    )

    email_password = config("EMAIL_PASSWORD", default=None)
    if not email_password:
        print("[DEV MODE] Email not sent (EMAIL_PASSWORD not configured)")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Template: {template}")
        return HttpResponse("Mail Send (Dev Mode)", status=200)

    mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    mail_server.ehlo()
    mail_server.login(config("ADMIN_EMAIL"), email_password)

    try:
        mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"], msg.as_string())
        log_email_sent(
            msg,
            email_type=template.replace(".html", ""),
            custom_message_content=custom_message_content,
        )
    except Exception as e:
        log_email_failed(
            to_email,
            subject,
            str(e),
            msg["From"],
            email_type=template.replace(".html", ""),
        )
        raise e
    finally:
        mail_server.quit()

    return HttpResponse("Mail Send", status=200)


def send_mail_batch(jobs):
    """
    Send multiple emails over one SMTP connection.
    Each job: {"subject": str, "template": str, "data": dict}
    """
    jobs = list(jobs)
    if not jobs:
        return

    email_password = config("EMAIL_PASSWORD", default=None)
    if not email_password:
        for job in jobs:
            print("[DEV MODE] Email not sent (EMAIL_PASSWORD not configured)")
            print(f"To: {job['data']['email']}")
            print(f"Subject: {job['subject']}")
            print(f"Template: {job['template']}")
        return

    logo_bytes = _get_static_image_bytes("f4u-h-final.png")
    checked_bytes = _get_static_image_bytes("checked.png")
    admin_email = config("ADMIN_EMAIL")

    mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    mail_server.ehlo()
    mail_server.login(admin_email, email_password)

    try:
        for job in jobs:
            template = job["template"]
            subject = job["subject"]
            data = job["data"]
            msg, to_email = _build_email_message(
                subject,
                template,
                data,
                logo_bytes=logo_bytes,
                checked_bytes=(
                    checked_bytes if template == "register-success.html" else None
                ),
            )
            try:
                mail_server.sendmail(admin_email, msg["To"], msg.as_string())
                log_email_sent(msg, email_type=template.replace(".html", ""))
            except Exception as e:
                log_email_failed(
                    to_email,
                    subject,
                    str(e),
                    msg["From"],
                    email_type=template.replace(".html", ""),
                )
    finally:
        mail_server.quit()


def send_admin_summary_email(admin_user, result):
    batch_id = str(uuid.uuid4())[:8]
    send_mail(
        f"Bulk Upload Summary [{batch_id}]",
        "bulk-upload-summary.html",
        {
            "name": admin_user.first_name or "Admin",
            "email": admin_user.email,
            "total_records": result["total_records"],
            "inserted": result["inserted"],
            "failed": result["failed"],
            "skipped": result["skipped"],
            "errors": result.get("errors", []),
        },
    )


def send_email_change_notification(old_email, new_email, user):
    send_mail(
        "Your Future4U Email Address Was Updated",
        "email-changed.html",
        {
            "name": user.first_name or "User",
            "email": old_email,
            "old_email": old_email,
            "new_email": new_email,
        },
    )


def send_activation_password_setup_email(user):
    from user.tasks import send_password_setup_link_task

    user.set_unusable_password()
    user.must_change_password = True
    user.otp = None
    user.otp_created_at = None
    user.save(
        update_fields=[
            "password",
            "must_change_password",
            "otp",
            "otp_created_at",
        ]
    )

    token = generate_token(user.email, WEB_PASSWORD_SETUP_TOKEN_DAYS)

    send_password_setup_link_task.delay(
        user.first_name,
        user.email,
        token,
    )
