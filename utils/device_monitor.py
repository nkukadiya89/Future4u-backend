import logging
import threading
import time

from device_config.models import DeviceConfiguration
from django.utils import timezone

logger = logging.getLogger(__name__)


class DeviceMonitor:
    _instance = None
    _lock = threading.Lock()
    _running = False
    _monitor_thread = None

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def start_monitoring(self, check_interval_minutes=5):
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(check_interval_minutes,), daemon=True
        )
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join()

    def _monitor_loop(self, check_interval_minutes):
        check_interval_seconds = check_interval_minutes * 60

        while self._running:
            try:
                self._check_all_devices()

                # Wait for next check
                for _ in range(check_interval_seconds):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in device monitor: {str(e)}")
                time.sleep(60)  # Wait 1 minute before retry

    def _check_all_devices(self):
        try:
            # Get all devices
            all_devices = DeviceConfiguration.objects.filter(
                deleted=False
            ).select_related("partner_company")

            online_count = 0
            offline_count = 0
            notifications_sent = 0

            for device in all_devices:
                if device.is_online:
                    online_count += 1
                else:
                    offline_count += 1

                    # Check if notification should be sent
                    if self._should_send_notification(device):
                        # Schedule notification using the same signal mechanism
                        from device_config.signals import schedule_offline_notification

                        schedule_offline_notification(device)
                        notifications_sent += 1

        except Exception as e:
            logger.error(f"Error checking devices: {str(e)}")

    def _should_send_notification(self, device):
        # Check if device has been offline for more than 2 hours
        hours_offline = self._get_hours_offline(device)
        if hours_offline < 2:
            return False

        # Check if notification was sent in last 2 hours
        last_notification = device.last_offline_notification
        if last_notification:
            hours_since_notification = (
                timezone.now() - last_notification
            ).total_seconds() / 3600
            if hours_since_notification < 2:
                return False

        # Only schedule if device has been offline for exactly 2 hours or more
        # and we haven't scheduled a notification recently
        return True

    def _get_hours_offline(self, device):
        if not device.updated_at:
            return 0
        return (timezone.now() - device.updated_at).total_seconds() / 3600


# Global monitor instance
device_monitor = DeviceMonitor()
