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

    app_url = config("APP_URL")
    if template == "register-success.html" or template == "verify_account.html":
        token = generate_token(data["email"], 30)
        context["login_url"] = app_url + "login"
        context["verify_link"] = app_url + "verify-success/"
        context["token"] = token
    elif template == "reset-pass.html":
        context["path"] = app_url + "reset-password/"
        context["token"] = data["token"]
    html_body = render_to_string(template, context)

    to_email = data["email"]

    msg = MIMEMultipart()
    msg.set_unixfrom("author")
    msg["From"] = "PROCEM <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = to_email
    msg["Subject"] = subject
    part2 = MIMEText(html_body, "html")
    msg.attach(part2)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    url = os.path.join(BASE_DIR, "static/images/procemlogo.png")
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

    mail_server.sendmail(config("ADMIN_EMAIL"), msg["To"], msg.as_string())

    mail_server.quit()
    return HttpResponse("Mail Send", status=200)
