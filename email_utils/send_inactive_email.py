import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.shortcuts import HttpResponse
from django.template.loader import render_to_string

from employee.models import Employee


def send_inactive_email(subject, template, data):
    context = {}

    employee_email = data.get("email", "")
    employee = Employee.objects.filter(email=employee_email).first()

    updated_by_employee = employee.updated_by
    updated_by_employee_email = updated_by_employee.email

    context.update(
        employee_id=employee.id,
        employee_name=employee.first_name,
        employee_last_name=employee.last_name,
        email=employee.email,
        deactivated_by_first_name=updated_by_employee.first_name if updated_by_employee else "System",
        updated_at=employee.updated_at,
    )

    html_body = render_to_string(template, context)
    super_admin_email = config("INIT_EMAIL")

    msg = MIMEMultipart()
    msg.set_unixfrom("author")
    msg["From"] = "OutdoorX <" + config("ADMIN_EMAIL") + ">"
    msg["To"] = employee_email
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

        recipients = [msg["To"], super_admin_email, updated_by_employee_email]

        mail_server.sendmail(config("ADMIN_EMAIL"), recipients, msg.as_string())
        mail_server.quit()

    except Exception as e:
        return HttpResponse(f"An error occurred while sending the email {e}", status=500)

    return HttpResponse("Mail Send", status=200)
