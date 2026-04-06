import os
import smtplib
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jwt
from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string

from utils.email_logger import log_email_failed, log_email_sent


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


def send_mail(subject, template, data):
    context = {}
    context["name"] = data["name"]
    custom_message_content = None  # Initialize custom message content

    app_url = config("APP_URL")
    if template == "register-success.html" or template == "verify_account.html":
        token = generate_token(data["email"], 30)
        context["login_url"] = app_url + "login"
        context["verify_link"] = app_url + "verify-success/"
        context["token"] = token
    elif template == "reset-pass.html":
        # Reset password flow link
        context["path"] = app_url + "reset-password/"
        token_value = data["token"]
        if isinstance(token_value, (bytes, bytearray)):
            token_value = token_value.decode("utf-8")
        context["token"] = str(token_value)
    elif template == "forgot-pass.html":
        # Forgot password flow link
        context["path"] = app_url + "forgot-password/"
        token_value = data["token"]
        if isinstance(token_value, (bytes, bytearray)):
            token_value = token_value.decode("utf-8")
        context["token"] = str(token_value)
    elif template == "device-config-status-update.html":
        # Device configuration status update
        context.update(
            {
                "device_name": data.get("device_name", "N/A"),
                "new_status": data.get("new_status", "Updated"),
                "updated_by": data.get("updated_by", "System"),
                "updated_at": data.get("updated_at", "Just now"),
                "login_url": data.get("login_url", app_url + "login"),
            }
        )

        # Create custom message content for EmailLog
        custom_message_content = "Device configuration status has been updated.\n"
        if data.get("device_name"):
            custom_message_content += f"Device: {data.get('device_name')},\n"
        if data.get("new_status"):
            custom_message_content += f"Status: {data.get('new_status')},\n"
        if data.get("updated_by"):
            custom_message_content += f"Updated By: {data.get('updated_by')}\n"
        if data.get("company_name"):
            custom_message_content += f"Company: {data.get('company_name')},\n"
    elif template == "device-transfer-status-update.html":
        # Device transfer status update
        context.update(
            {
                "device_name": data.get("device_name", "N/A"),
                "new_status": data.get("new_status", "Updated"),
                # "updated_by": data.get("updated_by", "System"),
                # "updated_at": data.get("updated_at", "Just now"),
                "login_url": data.get("login_url", app_url + "login"),
            }
        )

        # Create custom message content for EmailLog
        custom_message_content = "Device transfer status has been updated.\n"
        if data.get("device_name"):
            custom_message_content += f"Device: {data.get('device_name')},\n"
        if data.get("new_status"):
            custom_message_content += f"Status: {data.get('new_status')},\n"
        if data.get("updated_by"):
            custom_message_content += f"Updated By: {data.get('updated_by')}\n"
        if data.get("company_name"):
            custom_message_content += f"Company: {data.get('company_name')},\n"
    elif template == "campaign-id-generated.html":
        # Campaign ID generated
        context.update(
            {
                "campaign_id": data.get("campaign_id", "N/A"),
                "generated_date": data.get("generated_date", "N/A"),
                "end_client_name": data.get("end_client_name", "N/A"),
            }
        )
    elif template == "enquiry-notification.html":
        # Enquiry Notification
        context.update(
            {
                "name": data.get("name", "N/A"),
                "email": data.get("email", "N/A"),
                "enquirer_email": data.get("enquirer_email", "N/A"),
                "phone": data.get("phone", "N/A"),
                "message": data.get("message", "N/A"),
                "company_name": data.get("company_name", "N/A"),
                "company_email": data.get("company_email", "N/A"),
            }
        )

    html_body = render_to_string(template, context)

    to_email = data["email"]

    msg = MIMEMultipart()
    msg.set_unixfrom("author")
    msg["From"] = "OutdoorX <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = to_email
    msg["Subject"] = subject
    part2 = MIMEText(html_body, "html")
    msg.attach(part2)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    url = os.path.join(BASE_DIR, "static/images/e-switch-h-final.png")
    img_data = open(url, "rb").read()
    msImage = MIMEImage(img_data)
    msImage.add_header("Content-ID", "<image1>")
    msg.attach(msImage)

    if template == "register-success.html":
        url = os.path.join(BASE_DIR, "static/images/checked.png")
        img_data1 = open(url, "rb").read()
        msImage1 = MIMEImage(img_data1)
        msImage1.add_header("Content-ID", "<image2>")
        msg.attach(msImage1)

    mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    mail_server.ehlo()

    mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))

    try:
        mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"], msg.as_string())
        # Log successful email
        log_email_sent(
            msg,
            email_type=template.replace(".html", ""),
            custom_message_content=custom_message_content,
        )
    except Exception as e:
        # Log failed email
        log_email_failed(
            to_email,
            subject,
            str(e),
            msg["From"],
            email_type=template.replace(".html", ""),
        )
        raise e

    mail_server.quit()
    return HttpResponse("Mail Send", status=200)
