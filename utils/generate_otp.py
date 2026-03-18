import os
import random
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string


def generate_otp():
    otp = random.randint(1000, 9000)
    return otp


def send_otp_email(subject, template, data):
    context = {}

    app_url = config("APP_URL")
    if template == "account-otp.html":
        context["login_url"] = app_url + "login"
        context["verify_link"] = app_url + "verify-success/"
        context["name"] = data["name"]
        context["otp"] = data["otp"]
    else:
        template == "verify_email.html"
        context["otp"] = data["otp"]

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
