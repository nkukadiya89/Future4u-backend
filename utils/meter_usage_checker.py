"""
Meter Data Usage Checker
This module checks if total active energy usage reaches 70% of subscription limit
and sends notifications to company, partner company, and superadmin based on meter data.
"""

import logging
from datetime import timedelta

from django.utils.timezone import now
from decouple import config

from device_config.models import DeviceConfiguration, DeviceElectricalParameter
from company.models import Company
from email_utils.send_meter_usage_alert import send_meter_usage_alert_email

logger = logging.getLogger(__name__)


def check_meter_usage_alerts():
    """
    Check all devices' meter data usage in last 30 days
    Send alerts if total active energy reaches 70% of subscription limit
    """
    try:
        print("🔄 Checking meter usage alerts...")
        
        # Get date range for last 30 days
        end_date = now()
        start_date = end_date - timedelta(days=30)
        
        alerts_sent = 0
        
        # Get all active devices
        devices = DeviceConfiguration.objects.filter(
            deleted=False,
            status='active'
        ).select_related('partner_company')
        
        for device in devices:
            try:
                # Get company name from partner company or device details
                company_name = device.partner_company.company_name if device.partner_company else 'Unknown'
                
                # Get all total active energy data for this device in last 30 days
                device_energy_data = DeviceElectricalParameter.objects.filter(
                    device_configuration=device,
                    parameter_type="total_active_energy",
                    timestamp__range=[start_date, end_date]
                ).order_by('timestamp')
                
                if not device_energy_data.exists():
                    continue
                
                # Get the first and last values to calculate total usage over 30 days
                first_energy = device_energy_data.first()
                latest_energy = device_energy_data.last()
                
                if not first_energy or not latest_energy:
                    continue
                
                # Calculate total usage over 30 days (difference between first and last reading)
                total_usage_30_days = float(latest_energy.value) - float(first_energy.value)
                
                # Calculate expected daily average and what 70% of that would be
                if total_usage_30_days <= 0:
                    continue  # No positive usage detected
                
                daily_average = total_usage_30_days / 30
                expected_70_percent_usage = daily_average * 0.7
                
                # Get the most recent day's usage (last 24 hours)
                last_24h_start = end_date - timedelta(hours=24)
                recent_data = DeviceElectricalParameter.objects.filter(
                    device_configuration=device,
                    parameter_type="total_active_energy",
                    timestamp__range=[last_24h_start, end_date]
                ).order_by('timestamp')
                
                if recent_data.count() < 2:
                    continue  # Not enough data for recent usage calculation
                
                recent_first = recent_data.first()
                recent_last = recent_data.last()
                recent_usage = float(recent_last.value) - float(recent_first.value)
                
                # Check if recent usage is less than 70% of daily average
                if recent_usage < expected_70_percent_usage:
                    print(f"📊 Device {device.device_code}: Recent usage {recent_usage:.2f} < 70% of daily average {daily_average:.2f}")
                    
                    # Send alert email
                    alert_sent = send_meter_usage_alert_email(
                        device=device,
                        partner_company=device.partner_company,
                        company_name=company_name,
                        recent_usage=recent_usage,
                        daily_average=daily_average,
                        usage_percentage=(recent_usage / daily_average) * 100 if daily_average > 0 else 0
                    )
                    
                    if alert_sent:
                        alerts_sent += 1
                        print(f"📧 Meter usage alert sent for device: {device.device_code}")
                    else:
                        print(f"❌ Failed to send meter usage alert for device: {device.device_code}")
                        
            except Exception as e:
                print(f"❌ Error checking device {device.device_code}: {str(e)}")
                logger.error(f"Error checking meter usage for device {device.device_code}: {str(e)}")
                continue
        
        if alerts_sent > 0:
            print(f"✅ Sent {alerts_sent} meter usage alerts")
        else:
            print("✅ No meter usage alerts needed")
            
        return alerts_sent
        
    except Exception as e:
        print(f"❌ Error in check_meter_usage_alerts: {str(e)}")
        logger.error(f"Error in check_meter_usage_alerts: {str(e)}")
        return 0


def check_device_meter_usage(device_id):
    """
    Check meter usage for a specific device
    Useful for manual checks or API calls
    """
    try:
        device = DeviceConfiguration.objects.get(id=device_id)
        
        # Get company name from partner company or device details
        company_name = device.partner_company.company_name if device.partner_company else 'Unknown'
        
        # Calculate usage for last 30 days
        end_date = now()
        start_date = end_date - timedelta(days=30)
        
        # Get all total active energy data for this device in last 30 days
        device_energy_data = DeviceElectricalParameter.objects.filter(
            device_configuration=device,
            parameter_type="total_active_energy",
            timestamp__range=[start_date, end_date]
        ).order_by('timestamp')
        
        if not device_energy_data.exists():
            return {
                "success": False,
                "message": "No meter data found for this device in last 30 days"
            }
        
        # Get the first and last values to calculate total usage over 30 days
        first_energy = device_energy_data.first()
        latest_energy = device_energy_data.last()
        
        if not first_energy or not latest_energy:
            return {
                "success": False,
                "message": "Insufficient meter data for calculation"
            }
        
        # Calculate total usage over 30 days (difference between first and last reading)
        total_usage_30_days = float(latest_energy.value) - float(first_energy.value)
        
        # Calculate expected daily average and what 70% of that would be
        if total_usage_30_days <= 0:
            return {
                "success": False,
                "message": "No positive usage detected in last 30 days"
            }
        
        daily_average = total_usage_30_days / 30
        expected_70_percent_usage = daily_average * 0.7
        
        # Get the most recent day's usage (last 24 hours)
        last_24h_start = end_date - timedelta(hours=24)
        recent_data = DeviceElectricalParameter.objects.filter(
            device_configuration=device,
            parameter_type="total_active_energy",
            timestamp__range=[last_24h_start, end_date]
        ).order_by('timestamp')
        
        if recent_data.count() < 2:
            return {
                "success": False,
                "message": "Insufficient recent meter data for last 24 hours"
            }
        
        recent_first = recent_data.first()
        recent_last = recent_data.last()
        recent_usage = float(recent_last.value) - float(recent_first.value)
        
        usage_percentage = (recent_usage / daily_average) * 100 if daily_average > 0 else 0
        
        return {
            "success": True,
            "device_code": device.device_code,
            "company_name": company_name,
            "recent_usage": recent_usage,
            "daily_average": daily_average,
            "usage_percentage": usage_percentage,
            "expected_70_percent_usage": expected_70_percent_usage,
            "alert_needed": recent_usage < expected_70_percent_usage if daily_average > 0 else False,
            "period": f"Last 30 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
            "last_reading_time": latest_energy.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except DeviceConfiguration.DoesNotExist:
        return {
            "success": False,
            "message": "Device not found"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


def check_all_devices_usage():
    """
    Check usage for all devices and return summary
    """
    try:
        end_date = now()
        start_date = end_date - timedelta(days=30)
        
        devices_summary = []
        
        # Get all active devices
        devices = DeviceConfiguration.objects.filter(
            deleted=False,
            status='active'
        ).select_related('partner_company')
        
        for device in devices:
            # Get company name from partner company or device details
            company_name = device.partner_company.company_name if device.partner_company else 'Unknown'
            
            # Get all total active energy data for this device in last 30 days
            device_energy_data = DeviceElectricalParameter.objects.filter(
                device_configuration=device,
                parameter_type="total_active_energy",
                timestamp__range=[start_date, end_date]
            ).order_by('timestamp')
            
            if not device_energy_data.exists():
                continue
            
            # Get the first and last values to calculate total usage over 30 days
            first_energy = device_energy_data.first()
            latest_energy = device_energy_data.last()
            
            if not first_energy or not latest_energy:
                continue
            
            # Calculate total usage over 30 days (difference between first and last reading)
            total_usage_30_days = float(latest_energy.value) - float(first_energy.value)
            
            # Calculate expected daily average and what 70% of that would be
            if total_usage_30_days <= 0:
                continue  # No positive usage detected
            
            daily_average = total_usage_30_days / 30
            expected_70_percent_usage = daily_average * 0.7
            
            # Get the most recent day's usage (last 24 hours)
            last_24h_start = end_date - timedelta(hours=24)
            recent_data = DeviceElectricalParameter.objects.filter(
                device_configuration=device,
                parameter_type="total_active_energy",
                timestamp__range=[last_24h_start, end_date]
            ).order_by('timestamp')
            
            if recent_data.count() < 2:
                continue  # Not enough data for recent usage calculation
            
            recent_first = recent_data.first()
            recent_last = recent_data.last()
            recent_usage = float(recent_last.value) - float(recent_first.value)
            
            usage_percentage = (recent_usage / daily_average) * 100 if daily_average > 0 else 0
            
            devices_summary.append({
                "device_code": device.device_code,
                "company_name": company_name,
                "recent_usage": recent_usage,
                "daily_average": daily_average,
                "usage_percentage": usage_percentage,
                "alert_needed": recent_usage < expected_70_percent_usage if daily_average > 0 else False,
                "last_reading_time": latest_energy.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return {
            "success": True,
            "total_devices_checked": len(devices_summary),
            "devices_needing_alert": len([d for d in devices_summary if d["alert_needed"]]),
            "period": f"Last 30 days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
            "devices": devices_summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }
