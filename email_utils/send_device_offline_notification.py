import logging
import os
from datetime import timedelta
from email.mime.image import MIMEImage

from decouple import config
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from device_config.models import DeviceConfiguration
from utils.email_logger import log_email_failed, log_email_sent

logger = logging.getLogger(__name__)


def send_device_offline_notification(device, hours_offline=2):
    device_identifier = device.device_code or device.mac_address or f"ID:{device.id}"

    try:
        # Get superadmin email
        super_admin_email = config("INIT_EMAIL")

        # Get partner company email if available
        partner_company_email = None
        if device.partner_company and device.partner_company.email:
            partner_company_email = device.partner_company.email

        # Get site location details if available
        site_location = device.site_locations.first()
        site_details = {}
        if site_location:
            site_details = {
                "site_reference_id": site_location.site_reference_id or "N/A",
                "site_address": ", ".join(
                    filter(
                        None,
                        [
                            site_location.site_address_building,
                            site_location.site_address_landmark,
                            (
                                getattr(
                                    site_location.site_address_area,
                                    "city_area_name",
                                    None,
                                )
                                if hasattr(site_location, "site_address_area")
                                and site_location.site_address_area
                                else None
                            ),
                            (
                                getattr(site_location.site_address_city, "name", None)
                                if hasattr(site_location, "site_address_city")
                                and site_location.site_address_city
                                else None
                            ),
                            (
                                getattr(site_location.site_address_state, "name", None)
                                if hasattr(site_location, "site_address_state")
                                and site_location.site_address_state
                                else None
                            ),
                            site_location.site_address_pincode,
                        ],
                    )
                )
                or "N/A",
            }

        # Prepare email context
        device_name = device.device_code or device.mac_address
        context = {
            "device_name": device_name,
            "mac_address": device.mac_address or "N/A",
            "imei_number": device.imei_number or "N/A",
            "hours_offline": hours_offline,
            "last_seen": (
                device.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                if device.updated_at
                else "N/A"
            ),
            "device_status": (
                device.get_status_display()
                if hasattr(device, "get_status_display")
                else device.status
            ),
            "admin_url": getattr(settings, "ADMIN_URL", ""),
            "superadmin_name": "Super Administrator",
            "partner_company_name": (
                device.partner_company.company_name
                if device.partner_company and device.partner_company.company_name
                else "Partner Company"
            ),
            "site_details": site_details,
        }

        # Create custom message content for EmailLog
        device_name = device.device_code or device.mac_address
        custom_message_content = "Device offline notification.\n"
        custom_message_content += f"Device: {device_name},\n"
        custom_message_content += f"Status: {device.get_status_display() if hasattr(device, 'get_status_display') else device.status},\n"
        custom_message_content += f"Hours Offline: {int(hours_offline)},\n"
        if site_details and site_details != "N/A":
            site_ref_id = site_details.get("site_reference_id", "N/A")
            site_addr = site_details.get("site_address", "N/A")
            custom_message_content += f"Site: {site_ref_id} | {site_addr},\n"

        # Render email content
        subject = "Device Offline Notification"

        # Create separate emails for each recipient with personalized content
        emails_sent = 0

        # Email for Superadmin
        superadmin_context = context.copy()
        superadmin_context["recipient_name"] = "Super Administrator"
        superadmin_context["recipient_type"] = "superadmin"

        superadmin_html = render_to_string(
            "device_offline_notification.html", superadmin_context
        )
        superadmin_text = strip_tags(superadmin_html)

        superadmin_email = EmailMultiAlternatives(
            subject=subject,
            body=superadmin_text,
            from_email="OutdoorX <{}>".format(config("ADMIN_EMAIL")),
            to=[super_admin_email],
        )

        # Attach HTML content
        superadmin_email.attach_alternative(superadmin_html, "text/html")

        # Attach logo image
        logo_path = os.path.join(
            settings.BASE_DIR, "static", "images", "e-switch-h-final.png"
        )
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as image_file:
                img_data = image_file.read()
            logo_image = MIMEImage(img_data)
            logo_image.add_header("Content-ID", "<image1>")
            superadmin_email.attach(logo_image)

        try:
            superadmin_email.send()
            emails_sent += 1
            # Log successful email
            log_email_sent(
                superadmin_email,
                email_type="device_offline_notification",
                custom_message_content=custom_message_content,
                related_partner_company=device.partner_company,
            )
        except Exception as e:
            logger.error(f"Failed to send email to Superadmin: {str(e)}")
            # Log failed email
            log_email_failed(
                super_admin_email,
                subject,
                str(e),
                "OutdoorX <{}>".format(config("ADMIN_EMAIL")),
                email_type="device_offline_notification",
                related_partner_company=device.partner_company,
            )

        # Email for Partner Company (if exists)
        if partner_company_email:
            partner_context = context.copy()
            partner_context["recipient_name"] = (
                device.partner_company.company_name
                if device.partner_company and device.partner_company.company_name
                else "Partner Company"
            )
            partner_context["recipient_type"] = "partner"

            partner_html = render_to_string(
                "device_offline_notification.html", partner_context
            )
            partner_text = strip_tags(partner_html)

            partner_email_msg = EmailMultiAlternatives(
                subject=subject,
                body=partner_text,
                from_email="OutdoorX <{}>".format(config("ADMIN_EMAIL")),
                to=[partner_company_email],
            )

            # Attach HTML content
            partner_email_msg.attach_alternative(partner_html, "text/html")

            # Attach logo image
            logo_path = os.path.join(
                settings.BASE_DIR, "static", "images", "e-switch-h-final.png"
            )
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as image_file:
                    img_data = image_file.read()
                logo_image = MIMEImage(img_data)
                logo_image.add_header("Content-ID", "<image1>")
                partner_email_msg.attach(logo_image)

            try:
                partner_email_msg.send()
                emails_sent += 1
                # Log successful email
                log_email_sent(
                    partner_email_msg,
                    email_type="device_offline_notification",
                    custom_message_content=custom_message_content,
                    related_partner_company=device.partner_company,
                )
            except Exception as e:
                logger.error(f"Failed to send email to Partner Company: {str(e)}")
                # Log failed email
                log_email_failed(
                    partner_company_email,
                    subject,
                    str(e),
                    "OutdoorX <{}>".format(config("ADMIN_EMAIL")),
                    email_type="device_offline_notification",
                    related_partner_company=device.partner_company,
                )

        return emails_sent > 0

    except Exception as e:
        logger.error(
            f"Error sending offline notification for device {device_identifier}: {str(e)}"
        )
        return False


def check_offline_devices():
    try:
        from django.utils import timezone

        # Calculate the time threshold (2 hours ago)
        time_threshold = timezone.now() - timedelta(hours=2)

        # Get devices that are offline and were last updated more than 2 hours ago
        offline_devices = DeviceConfiguration.objects.filter(
            is_online=False, updated_at__lte=time_threshold, deleted=False
        ).select_related("partner_company")

        sent_count = 0
        for device in offline_devices:
            # Calculate hours offline
            hours_offline = (timezone.now() - device.updated_at).total_seconds() / 3600

            # Only send notification if it's been more than 2 hours
            if hours_offline >= 2:
                # Check if we've already sent a notification in the last 2 hours
                last_notification_sent = getattr(
                    device, "last_offline_notification", None
                )
                if (
                    last_notification_sent
                    and (timezone.now() - last_notification_sent).total_seconds() < 7200
                ):
                    continue  # Skip if we've already sent a notification in the last 2 hours

                # Send notification
                if send_device_offline_notification(device, int(hours_offline)):
                    # Update the last notification time
                    device.last_offline_notification = timezone.now()
                    device.save(update_fields=["last_offline_notification"])
                    sent_count += 1

        logger.info(f"Sent offline notifications for {sent_count} devices")
        return sent_count

    except Exception as e:
        logger.error(f"Error checking offline devices: {str(e)}")
        return 0
