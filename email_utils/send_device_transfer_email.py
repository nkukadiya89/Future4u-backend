import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from decouple import config
from django.http import HttpResponse
from django.template.loader import render_to_string

from utils.email_logger import log_email_failed, log_email_sent


def send_device_transfer_request_email(subject, template, data):
    context = {
        "name": data.get("name"),
        "email": data.get("email"),
        "company_name": data.get("company_name"),
        # "partner_company_name": data.get("partner_company_name"),
        "total_sites": data.get("total_sites"),
        "site_list": data.get("site_list", []),
    }

    html_body = render_to_string(template, context)

    # Create custom message content for EmailLog
    custom_message_content = "A new device transfer request has been created.\n"
    if data.get("company_name"):
        custom_message_content += f"Company: {data.get('company_name')},\n"

    # Add site addresses if available
    site_list = data.get("site_list", [])
    if site_list:
        for site in site_list:
            if isinstance(site, dict):
                reference = site.get("reference", "")
                address = site.get("address", "")
                if reference and address:
                    custom_message_content += f"Site Address: {reference} | {address}\n"
            elif hasattr(site, "reference") and hasattr(site, "address"):
                custom_message_content += (
                    f"Site Address: {site.reference} | {site.address}\n"
                )

    recipient_email = data["email"]

    msg = MIMEMultipart()
    msg["From"] = "Future4U <" + config("ADMIN_EMAIL") + ">"

    msg["To"] = recipient_email
    msg["Subject"] = subject

    part2 = MIMEText(html_body, "html")
    msg.attach(part2)

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        url = os.path.join(BASE_DIR, "static/images/f4u-h-final.png")
        with open(url, "rb") as image_file:
            img_data = image_file.read()
        msImage = MIMEImage(img_data)
        msImage.add_header("Content-ID", "<image1>")
        msg.attach(msImage)
    except Exception:
        pass

    try:
        mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        mail_server.ehlo()
        mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))

        recipients = msg["To"].split(", ")
        mail_server.sendmail(config("ADMIN_EMAIL"), recipients, msg.as_string())
        mail_server.quit()

        # Log successful emails for all recipients
        for recipient in recipients:
            log_email_sent(
                msg,
                email_type=template.replace(".html", ""),
                custom_message_content=custom_message_content,
            )

        return HttpResponse("Mail Sent", status=200)
    except Exception as e:
        # Log failed email
        log_email_failed(
            msg["To"],
            subject,
            str(e),
            msg["From"],
            email_type=template.replace(".html", ""),
        )
        return HttpResponse(f"Mail could not be sent: {str(e)}", status=500)
