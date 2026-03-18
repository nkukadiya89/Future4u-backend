import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string


def send_whatsapp_message_failed_mail(subject, template, data):
    context = {
        "phone_number": data.get("phone_number"),
        "template_name": data.get("template_name"),
        "activity": data.get("activity"),
        "response_code": data.get("response_code"),
        "response_content": data.get("response_content"),
        "request_user": data.get("request_user", None),
        "company": data.get("company", None),
        "employee": data.get("employee", None),
    }

    html_body = render_to_string(template, context)

    to_email = config("WHATSAPP_MESSAGE_FAILED_EMAIL")

    msg = MIMEMultipart()
    msg.set_unixfrom("author")
    msg["From"] = "OutdoorX <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = to_email
    msg["BCC"] = "quartzkhatri@gmail.com"
    msg["Subject"] = subject
    part2 = MIMEText(html_body, "html")
    msg.attach(part2)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    url = os.path.join(BASE_DIR, "static/images/e-switch-h-final.png")
    img_data = open(url, "rb").read()
    msImage = MIMEImage(img_data)
    msImage.add_header("Content-ID", "<image1>")
    msg.attach(msImage)

    try:
        mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        mail_server.ehlo()
        mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))

        recipients = [msg["To"], msg["BCC"]]
        mail_server.sendmail(config("ADMIN_EMAIL"), recipients, msg.as_string())

        mail_server.quit()
        return HttpResponse("Mail Sent", status=200)

    except Exception as e:
        return HttpResponse(f"Mail could not be sent: {str(e)}", status=500)
