import logging

from django.utils import timezone

from device_config.models import DeviceConfiguration

logger = logging.getLogger(__name__)


def check_existing_offline_devices():
    try:
        # Get all devices that are currently offline
        offline_devices = DeviceConfiguration.objects.filter(
            is_online=False, deleted=False
        ).select_related("partner_company")

        scheduled_count = 0
        for device in offline_devices:
            device_identifier = (
                device.device_code or device.mac_address or f"ID:{device.id}"
            )
            # Calculate how long the device has been offline
            if device.updated_at:
                hours_offline = (
                    timezone.now() - device.updated_at
                ).total_seconds() / 3600

                if hours_offline >= 2:
                    # Check if we've already sent a notification in the last 2 hours
                    last_notification = device.last_offline_notification
                    if last_notification:
                        # Calculate how long since last notification
                        time_since_last_notification = (
                            timezone.now() - last_notification
                        ).total_seconds() / 3600
                        if time_since_last_notification < 2:
                            # Schedule notification for devices that have been offline for more than 2 hours
                            from device_config.signals import (
                                schedule_offline_notification,
                            )

                            schedule_offline_notification(device)
                            scheduled_count += 1
                            logger.info(
                                f"Scheduled offline notification for device {device_identifier}"
                            )

        logger.info(
            f"Scheduled notifications for {scheduled_count} existing offline devices"
        )

    except Exception as e:
        logger.error(f"Error checking existing offline devices: {str(e)}")
        return 0
