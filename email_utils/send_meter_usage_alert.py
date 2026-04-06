import logging
import os

from decouple import config
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from utils.email_logger import log_email_failed, log_email_sent

logger = logging.getLogger(__name__)


def send_meter_usage_alert_email(
    device, partner_company, company_name, recent_usage, daily_average, usage_percentage
):
    """
    Send meter usage alert email to partner company and superadmin

    Args:
        device: DeviceConfiguration object
        recent_usage: Recent usage (last 24 hours)
        daily_average: Daily average usage over last 30 days
        usage_percentage: Usage percentage compared to daily average

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Calculate expected 70% usage
        expected_70_percent_usage = daily_average * 0.7

        # Get email recipients
        recipients = []

        # 1. Add partner company email
        if device.partner_company and device.partner_company.email:
            recipients.append(device.partner_company.email)

        # 2. Add superadmin email
        superadmin_email = config("INIT_EMAIL", default="")
        if superadmin_email:
            recipients.append(superadmin_email)

        if not recipients:
            logger.warning(f"No email recipients found for device {device.device_code}")
            return False

        # Prepare email context
        context = {
            "device_code": device.device_code,
            "device_id": device.id,
            "company_name": company_name,
            "partner_company_name": (
                device.partner_company.company_name if device.partner_company else None
            ),
            "recent_usage": recent_usage,
            "daily_average": daily_average,
            "usage_percentage": usage_percentage,
            "expected_70_percent_usage": expected_70_percent_usage,
            "admin_url": config("ADMIN_URL", default="http://127.0.0.1:8000/admin/"),
            "recipient_name": company_name,
        }

        # Render email template
        html_content = render_to_string("meter-usage-alert.html", context)
        text_content = strip_tags(html_content)

        # Email configuration
        from_email = config("DEFAULT_FROM_EMAIL")
        subject = f"📉 Low Usage Alert: Device {device.device_code} at {usage_percentage:.1f}% of daily average"

        # Send email to all recipients
        for recipient_email in recipients:
            try:
                # Create email with logo attachment
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[recipient_email],
                )
                email.attach_alternative(html_content, "text/html")

                # Send basic email first
                email.send()

                # Attach logo image
                try:
                    BASE_DIR = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    logo_path = os.path.join(
                        BASE_DIR, "static/images/e-switch-h-final.png"
                    )
                    with open(logo_path, "rb") as image_file:
                        img_data = image_file.read()

                    from email.mime.image import MIMEImage
                    from email.mime.multipart import MIMEMultipart

                    # Create a new message with logo
                    msg = MIMEMultipart()
                    msg["From"] = from_email
                    msg["To"] = recipient_email
                    msg["Subject"] = subject

                    # Attach HTML content
                    from email.mime.text import MIMEText

                    html_part = MIMEText(html_content, "html")
                    msg.attach(html_part)

                    # Attach logo
                    logo_image = MIMEImage(img_data)
                    logo_image.add_header("Content-ID", "<image1>")
                    msg.attach(logo_image)

                    # Send email with logo
                    import smtplib

                    mail_server = smtplib.SMTP("smtp.gmail.com", 587, timeout=60)
                    mail_server.ehlo()
                    mail_server.starttls()
                    mail_server.ehlo()
                    mail_server.login(config("ADMIN_EMAIL"), config("EMAIL_PASSWORD"))
                    mail_server.sendmail(from_email, [recipient_email], msg.as_string())
                    mail_server.quit()

                except Exception as logo_error:
                    # If logo attachment fails, the basic email was already sent
                    logger.warning(
                        f"Logo attachment failed but email was sent to {recipient_email}: {str(logo_error)}"
                    )

                # Log successful email
                log_email_sent(
                    email_obj=email,
                    email_type="meter_usage_alert",
                    related_device=device,
                    sender_id=1,  # System sender
                )

                logger.info(
                    f"Meter usage alert email sent successfully to {recipient_email}"
                )

            except Exception as e:
                logger.error(
                    f"Failed to send meter usage alert email to {recipient_email}: {str(e)}"
                )

                # Log failed email
                log_email_failed(
                    recipient_email=recipient_email,
                    subject=subject,
                    error_message=str(e),
                    sender_email=from_email,
                    email_type="meter_usage_alert",
                    related_device=device,
                    sender_id=1,  # System sender
                )

        return True

    except Exception as e:
        logger.error(f"Failed to send meter usage alert email: {str(e)}")
        return False
