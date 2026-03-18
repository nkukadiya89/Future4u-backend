from django.conf import settings
from django.db import models
from django.utils.timezone import now

from city_areas.models import CityArea
from company.models import Company, CompanyPhoto
from country.models import Country
from end_client.models import EndClient
from faq.models import FAQ
from partner_company.models import PartnerCompany, PartnerCompanyDocument
from subscription.models import Subscription, SubscriptionFeature, SubscriptionInvoice
from user.models import User
from user_profile.models import BusinessSetting


class WhatsAppMessageLog(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_whatsapp_logs",
    )

    phone_number = models.CharField(max_length=15)
    request_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="request_user_whatsapp_logs",
    )
    template_name = models.CharField(max_length=255)
    response_code = models.IntegerField()
    response_content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=now)
    activity = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.phone_number} - {self.template_name} - {self.activity}"

    class Meta:
        db_table = "whatsapp_message_log"


class EventQuerySet(models.QuerySet):
    def create(self, event_type, *args, **kwargs):
        kwargs["event_type"] = event_type
        super().create(**kwargs)


class EventCreater(object):
    @staticmethod
    def company_create(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_CREATE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_update(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_MODIFY,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_archive(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_ARCHIVE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_restore(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_RESTORE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_logo_delete(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_LOGO_DELETE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_photo_create(company_photo, ip_address, user, company):
        company_name = company.name if company else "Unknown Company"
        details = f"{company_name} - {company_photo.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_PHOTO_CREATE,
            company=company,
            company_photo=company_photo,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_photo_modify(company_photo, ip_address, user, company):
        company_name = company.name if company else "Unknown Company"
        details = f"{company_name} - {company_photo.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_PHOTO_MODIFY,
            company=company,
            company_photo=company_photo,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_photo_delete(company_photo, ip_address, user, company):
        company_name = company.name if company else "Unknown Company"
        details = f"{company_name} - {company_photo.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_PHOTO_DELETE,
            company=company,
            company_photo=company_photo,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_company_basic_info(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_BASIC_INFO_UPDATE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def change_company_password(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_CHANGE_PASSWORD,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_company_status(company, ip_address, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_STATUS_UPDATE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Partner Company
    @staticmethod
    def partner_company_create(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email if user else 'System'}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_CREATE,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_update(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_MODIFY,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_archive(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_ARCHIVE,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_restore(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_RESTORE,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_partner_company_basic_info(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_BASIC_INFO_UPDATE,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def change_partner_company_password(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_CHANGE_PASSWORD,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_partner_company_status(partner_company, ip_address, user):
        details = f"{partner_company.company_name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_STATUS_UPDATE,
            partner_company=partner_company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Partner Company Document
    @staticmethod
    def partner_company_document_create(partner_company_document, ip_address, user, partner_company):
        details = f"{partner_company_document.partner_company} - {partner_company_document.document_title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_CREATE,
            partner_company_document=partner_company_document,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_document_modify(partner_company_document, ip_address, user, partner_company):
        details = f"{partner_company_document.partner_company} - {partner_company_document.document_title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_MODIFY,
            partner_company_document=partner_company_document,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_document_archive(partner_company_document, ip_address, user, partner_company):
        details = f"{partner_company_document.partner_company} - {partner_company_document.document_title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_ARCHIVE,
            partner_company_document=partner_company_document,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def partner_company_document_restore(partner_company_document, ip_address, user, partner_company):
        details = f"{partner_company_document.partner_company} - {partner_company_document.document_title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_RESTORE,
            partner_company_document=partner_company_document,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    # EndClient
    @staticmethod
    def end_client_create(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_CREATE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def end_client_update(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_MODIFY,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def end_client_archive(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_ARCHIVE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def end_client_restore(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_RESTORE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def end_client_photo_delete(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_PHOTO_DELETE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_end_client_basic_info(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_BASIC_INFO_UPDATE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def change_end_client_password(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_CHANGE_PASSWORD,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def update_end_client_status(end_client, ip_address, user):
        details = f"{end_client.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_END_CLIENT_STATUS_UPDATE,
            end_client=end_client,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Employee
    @staticmethod
    def employee_create(employee, ip_address, user, company, partner_company):
        details = f"{employee.first_name} - {employee.last_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_CREATE,
            employee=employee,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
            partner_company=partner_company,
        )

    @staticmethod
    def employee_modify(employee, ip_address, user, company, partner_company):
        details = f"{employee.first_name} - {employee.last_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_MODIFY,
            employee=employee,
            ip_address=ip_address,
            user=user,
            details=details,
            company=company,
            partner_company=partner_company,
        )

    @staticmethod
    def employee_archive(employee, ip_address, user, company, partner_company):
        details = f"{employee.first_name} - {employee.last_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_ARCHIVE,
            employee=employee,
            ip_address=ip_address,
            user=user,
            details=details,
            company=company,
            partner_company=partner_company,
        )

    @staticmethod
    def employee_restore(employee, ip_address, user, company, partner_company):
        details = f"{employee.first_name} - {employee.last_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_RESTORE,
            employee=employee,
            ip_address=ip_address,
            user=user,
            details=details,
            company=company,
            partner_company=partner_company,
        )

    # Country
    @staticmethod
    def country_create(country, ip_address, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COUNTRY_CREATE,
            country=country,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def country_update(country, ip_address, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COUNTRY_MODIFY,
            country=country,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def country_archive(country, ip_address, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COUNTRY_ARCHIVE,
            country=country,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def country_restore(country, ip_address, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COUNTRY_RESTORE,
            country=country,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # State
    @staticmethod
    def state_create(state, ip_address, user):
        details = f"State: {state.name} - Country: {state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_STATE_CREATE,
            state=state,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def state_update(state, ip_address, user):
        details = f"State: {state.name} - Country: {state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_STATE_MODIFY,
            state=state,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def state_archive(state, ip_address, user):
        details = f"State: {state.name} - Country: {state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_STATE_ARCHIVE,
            state=state,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def state_restore(state, ip_address, user):
        details = f"State: {state.name} - Country: {state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_STATE_RESTORE,
            state=state,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # City
    @staticmethod
    def city_create(city, ip_address, user):
        details = f"City: {city.name} - State: {city.state.name}- Country{city.state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_CREATE,
            city=city,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_update(city, ip_address, user):
        details = f"City: {city.name} - State: {city.state.name}- Country{city.state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_MODIFY,
            city=city,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_archive(city, ip_address, user):
        details = f"City: {city.name} - State: {city.state.name}- Country{city.state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_ARCHIVE,
            city=city,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_restore(city, ip_address, user):
        details = f"City: {city.name} - State: {city.state.name}- Country{city.state.country.name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_RESTORE,
            city=city,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # City Area
    @staticmethod
    def city_area_create(city_area, ip_address, user):
        details = (
            f"City Area: {city_area.city_area_name} - Zipcode: {city_area.zipcode} - "
            f"City: {city_area.city.name} - State: {city_area.state.name} - "
            f"Country: {city_area.country.name}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_AREA_CREATE,
            city_area=city_area,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_area_update(city_area, ip_address, user):
        details = (
            f"City Area: {city_area.city_area_name} - Zipcode: {city_area.zipcode} - "
            f"City: {city_area.city.name} - State: {city_area.state.name} - "
            f"Country: {city_area.country.name}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_AREA_MODIFY,
            city_area=city_area,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_area_archive(city_area, ip_address, user):
        details = (
            f"City Area: {city_area.city_area_name} - Zipcode: {city_area.zipcode} - "
            f"City: {city_area.city.name} - State: {city_area.state.name} - "
            f"Country: {city_area.country.name}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_AREA_ARCHIVE,
            city_area=city_area,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def city_area_restore(city_area, ip_address, user):
        details = (
            f"City Area: {city_area.city_area_name} - Zipcode: {city_area.zipcode} - "
            f"City: {city_area.city.name} - State: {city_area.state.name} - "
            f"Country: {city_area.country.name}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CITY_AREA_RESTORE,
            city_area=city_area,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Business Category
    @staticmethod
    def business_category_create(business_category, ip_address, user):
        details = f"{business_category}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_CATEGORY_CREATE,
            business_category=business_category,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def business_category_update(business_category, ip_address, user):
        details = f"{business_category}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_CATEGORY_MODIFY,
            business_category=business_category,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def business_category_archive(business_category, ip_address, user):
        details = f"{business_category}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_CATEGORY_ARCHIVE,
            business_category=business_category,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def business_category_restore(business_category, ip_address, user):
        details = f"{business_category}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_CATEGORY_RESTORE,
            business_category=business_category,
            user=user,
            details=details,
            ip_address=ip_address,
        )
    
    # Notification Template
    @staticmethod
    def notification_template_create(notification_template, ip_address, user):
        details = f"{notification_template.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_NOTIFICATION_TEMPLATE_CREATE,
            notification_template=notification_template,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def notification_template_update(notification_template, ip_address, user):
        details = f"{notification_template.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_NOTIFICATION_TEMPLATE_MODIFY,
            notification_template=notification_template,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def notification_template_archive(notification_template, ip_address, user):
        details = f"{notification_template.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_NOTIFICATION_TEMPLATE_ARCHIVE,
            notification_template=notification_template,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def notification_template_restore(notification_template, ip_address, user):
        details = f"{notification_template.title}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_NOTIFICATION_TEMPLATE_RESTORE,
            notification_template=notification_template,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # site location
    @staticmethod
    def site_location_create(site_location, ip_address, user, company):
        state_name = site_location.site_address_state.name if site_location.site_address_state else "N/A"
        city_name = site_location.site_address_city.name if site_location.site_address_city else "N/A"
        holding_types = site_location.holding_types.name if site_location.holding_types else "N/A"
        details = f"{state_name} - {city_name} - {holding_types}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SITE_LOCATION_CREATE,
            site_location=site_location,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def site_location_modify(site_location, ip_address, user, company):
        state_name = site_location.site_address_state.name if site_location.site_address_state else "N/A"
        city_name = site_location.site_address_city.name if site_location.site_address_city else "N/A"
        holding_types = site_location.holding_types.name if site_location.holding_types else "N/A"
        details = f"{state_name} - {city_name} - {holding_types}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SITE_LOCATION_MODIFY,
            site_location=site_location,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def site_location_archive(site_location, ip_address, user, company):
        state_name = site_location.site_address_state.name if site_location.site_address_state else "N/A"
        city_name = site_location.site_address_city.name if site_location.site_address_city else "N/A"
        holding_types = site_location.holding_types.name if site_location.holding_types else "N/A"
        details = f"{state_name} - {city_name} - {holding_types}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SITE_LOCATION_ARCHIVE,
            site_location=site_location,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def site_location_restore(site_location, ip_address, user, company):
        company_name = site_location.company.name if site_location.company else "N/A"
        state_name = site_location.site_address_state.name if site_location.site_address_state else "N/A"
        city_name = site_location.site_address_city.name if site_location.site_address_city else "N/A"
        holding_types = site_location.holding_types.name if site_location.holding_types else "N/A"
        details = f"{company_name} - {state_name} - {city_name} - {holding_types}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SITE_LOCATION_RESTORE,
            site_location=site_location,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    # Request DEmo
    @staticmethod
    def request_demo_create(request_demo, ip_address, user):
        details = f"{request_demo.name} - {request_demo.demo_date}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_REQUEST_DEMO_CREATE,
            request_demo=request_demo,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def request_demo_update(request_demo, user):
        details = f"{request_demo.name} - {request_demo.demo_date}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_REQUEST_DEMO_MODIFY,
            request_demo=request_demo,
            user=user,
            details=details,
        )

    @staticmethod
    def request_demo_archive(request_demo, user):
        details = f"{request_demo.name} - {request_demo.demo_date}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_REQUEST_DEMO_ARCHIVE,
            request_demo=request_demo,
            user=user,
            details=details,
        )

    @staticmethod
    def request_demo_restore(request_demo, user):
        details = f"{request_demo.name} - {request_demo.demo_date}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_REQUEST_DEMO_RESTORE,
            request_demo=request_demo,
            user=user,
            details=details,
        )

    # Subscrpiton
    @staticmethod
    def subscription_create(subscription, ip_address, user):
        details = f"{subscription.package_name} - {subscription.subscription_type} - " f"{subscription.status}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_CREATE,
            subscription=subscription,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_update(subscription, ip_address, user):
        details = f"{subscription.package_name} - {subscription.subscription_type} - " f"{subscription.status}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_MODIFY,
            subscription=subscription,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_archive(subscription, ip_address, user):
        details = f"{subscription.package_name} - {subscription.subscription_type} - " f"{subscription.status}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_ARCHIVE,
            subscription=subscription,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_restore(subscription, ip_address, user):
        details = f"{subscription.package_name} - {subscription.subscription_type} - " f"{subscription.status}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_RESTORE,
            subscription=subscription,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Purchased subscription
    @staticmethod
    def subscription_invoice_create(subscription_invoice, ip_address, user):
        details = f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_invoice_update(subscription_invoice, ip_address, user):
        details = f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_invoice_archive(subscription_invoice, ip_address, user):
        details = f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_invoice_restore(subscription_invoice, ip_address, user):
        details = f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Subscription Feature
    @staticmethod
    def subscription_feature_create(subscription_feature, ip_address, user):
        details = (
            f"{subscription_feature.subscription} - {subscription_feature.feature_name} - "
            f"{subscription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_FEATURE_CREATE,
            subscription_feature=subscription_feature,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_feature_update(subscription_feature, ip_address, user):
        details = (
            f"{subscription_feature.subscription} - {subscription_feature.feature_name} - "
            f"{subscription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_FEATURE_MODIFY,
            subscription_feature=subscription_feature,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_feature_archive(subscription_feature, ip_address, user):
        details = (
            f"{subscription_feature.subscription} - {subscription_feature.feature_name} - "
            f"{subscription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_FEATURE_ARCHIVE,
            subscription_feature=subscription_feature,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_feature_restore(subscription_feature, ip_address, user):
        details = (
            f"{subscription_feature.subscription} - {subscription_feature.feature_name} - "
            f"{subscription_feature.feature_status_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBSCRIPTION_FEATURE_RESTORE,
            subscription_feature=subscription_feature,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Zone name
    @staticmethod
    def zone_name_create(zone_name, ip_address, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            ActivityLog.EVENT_TYPE_ZONE_NAME_CREATE,
            zone_name=zone_name,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def zone_name_update(zone_name, ip_address, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            ActivityLog.EVENT_TYPE_ZONE_NAME_MODIFY,
            zone_name=zone_name,
            user=user,
            ip_address=ip_address,
            details=details,
        )

    @staticmethod
    def zone_name_archive(zone_name, ip_address, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            ActivityLog.EVENT_TYPE_ZONE_NAME_ARCHIVE,
            zone_name=zone_name,
            user=user,
            ip_address=ip_address,
            details=details,
        )

    @staticmethod
    def zone_name_restore(zone_name, ip_address, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            ActivityLog.EVENT_TYPE_ZONE_NAME_RESTORE,
            zone_name=zone_name,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Business Setting
    @staticmethod
    def business_setting_update(business_setting, ip_address, user, company, partner_company):
        company_name = business_setting.company.name if business_setting.company else "N/A"
        partner_company_name = (
            business_setting.partner_company.company_name if business_setting.partner_company else "N/A"
        )
        details = (
            f"Company: {company_name} - Partner Company: {partner_company_name} - "
            f"Country: {business_setting.country}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_SETTING_MODIFY,
            business_setting=business_setting,
            user=user,
            details=details,
            company=company,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    # FAQ
    @staticmethod
    def faq_create(faq, ip_address, user):
        details = (
            f"FAQ: {faq.question[:50]}{'...' if len(faq.question) > 50 else ''} - {user.email if user else 'System'}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FAQ_CREATE,
            faq=faq,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def faq_update(faq, ip_address, user):
        details = (
            f"FAQ: {faq.question[:50]}{'...' if len(faq.question) > 50 else ''} - {user.email if user else 'System'}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FAQ_MODIFY,
            faq=faq,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def faq_archive(faq, ip_address, user):
        details = (
            f"FAQ: {faq.question[:50]}{'...' if len(faq.question) > 50 else ''} - {user.email if user else 'System'}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FAQ_ARCHIVE,
            faq=faq,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def faq_restore(faq, ip_address, user):
        details = (
            f"FAQ: {faq.question[:50]}{'...' if len(faq.question) > 50 else ''} - {user.email if user else 'System'}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FAQ_RESTORE,
            faq=faq,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    # Meter Config
    @staticmethod
    def meter_config_create(meter_config, ip_address, user, partner_company):
        details = f"{meter_config.meter_name} - {meter_config.phase_type} - SlaveID: {meter_config.slaveID}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_METER_CONFIG_CREATE,
            meter_config=meter_config,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def meter_config_update(meter_config, ip_address, user, partner_company):
        details = f"{meter_config.meter_name} - {meter_config.phase_type} - SlaveID: {meter_config.slaveID}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_METER_CONFIG_MODIFY,
            meter_config=meter_config,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def meter_config_archive(meter_config, ip_address, user, partner_company):
        details = f"{meter_config.meter_name} - {meter_config.phase_type} - SlaveID: {meter_config.slaveID}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_METER_CONFIG_ARCHIVE,
            meter_config=meter_config,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def meter_config_restore(meter_config, ip_address, user, partner_company):
        details = f"{meter_config.meter_name} - {meter_config.phase_type} - SlaveID: {meter_config.slaveID}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_METER_CONFIG_RESTORE,
            meter_config=meter_config,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    # Device Configuration
    @staticmethod
    def device_configuration_create(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_CREATE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_assign(device_configuration, ip_address, user, company):
        device_identifier = (
            device_configuration.imei_number
            or device_configuration.mac_address
            or device_configuration.device_code
            or f"Device #{device_configuration.id}"
        )
        details = f"{device_identifier}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_ASSIGN,
            device_configuration=device_configuration,
            user=user,
            company=company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_edit_site(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_EDIT_SITE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_update_status(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_STATUS,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_create_schedule(
        device_configuration, ip_address, user, partner_company=None, company=None
    ):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_CREATE_SCHEDULE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            company=company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_update_schedule(
        device_configuration, ip_address, user, partner_company=None, company=None
    ):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_SCHEDULE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            company=company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_power_control(device_configuration, ip_address, user, partner_company=None, company=None):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_POWER_CONTROL,
            device_configuration=device_configuration,
            user=user,
            company=company,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_update(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_MODIFY,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_archive(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_ARCHIVE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_configuration_restore(device_configuration, ip_address, user, partner_company):
        details = f"{device_configuration.imei_number} - {device_configuration.mac_address}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_CONFIGURATION_RESTORE,
            device_configuration=device_configuration,
            user=user,
            partner_company=partner_company,
            details=details,
            ip_address=ip_address,
        )

    # Device Transfer
    @staticmethod
    def device_transfer_site_photo_delete(device_transfer, ip_address, user):
        details = f"{device_transfer.current_device_config.device_code} - Site Photo Delete"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_SITE_PHOTO_DELETE,
            device_transfer=device_transfer,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def device_transfer_edit_request(device_transfer, ip_address, user, partner_company):
        details = f"{device_transfer.current_device_config.device_code} - Edit Request"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_EDIT_REQUEST,
            device_transfer=device_transfer,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def device_transfer_update_status(device_transfer, ip_address, user, partner_company):
        details = f"{device_transfer.current_device_config.device_code} - Update Status"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_UPDATE_STATUS,
            device_transfer=device_transfer,
            user=user,
            details=details,
            partner_company=partner_company,
            ip_address=ip_address,
        )

    @staticmethod
    def device_transfer_create(device_transfer, ip_address, user, company):
        company_name = device_transfer.company.name if device_transfer.company else "N/A"
        device_code = (
            device_transfer.current_device_config.device_code if device_transfer.current_device_config else "N/A"
        )
        details = f"{company_name} - {device_code}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_CREATE,
            device_transfer=device_transfer,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def device_transfer_update(device_transfer, ip_address, user, company):
        company_name = device_transfer.company.name if device_transfer.company else "N/A"
        device_code = (
            device_transfer.current_device_config.device_code if device_transfer.current_device_config else "N/A"
        )
        details = f"{company_name} - {device_code}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_UPDATE,
            device_transfer=device_transfer,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def device_transfer_archive(device_transfer, ip_address, user, company):
        company_name = device_transfer.company.name if device_transfer.company else "N/A"
        device_code = (
            device_transfer.current_device_config.device_code if device_transfer.current_device_config else "N/A"
        )
        details = f"{company_name} - {device_code}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_ARCHIVE,
            device_transfer=device_transfer,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def device_transfer_restore(device_transfer, ip_address, user, company):
        company_name = device_transfer.company.name if device_transfer.company else "N/A"
        device_code = (
            device_transfer.current_device_config.device_code if device_transfer.current_device_config else "N/A"
        )
        details = f"{company_name} - {device_code}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DEVICE_TRANSFER_RESTORE,
            device_transfer=device_transfer,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )


class ActivityLog(models.Model):
    EVENT_TYPE_STATE_CREATE = "state:create"
    EVENT_TYPE_STATE_MODIFY = "state:update"
    EVENT_TYPE_STATE_ARCHIVE = "state:archive"
    EVENT_TYPE_STATE_RESTORE = "state:restore"

    EVENT_TYPE_CITY_CREATE = "city:create"
    EVENT_TYPE_CITY_MODIFY = "city:update"
    EVENT_TYPE_CITY_ARCHIVE = "city:archive"
    EVENT_TYPE_CITY_RESTORE = "city:restore"

    EVENT_TYPE_CITY_AREA_CREATE = "city_area:create"
    EVENT_TYPE_CITY_AREA_MODIFY = "city_area:update"
    EVENT_TYPE_CITY_AREA_ARCHIVE = "city_area:archive"
    EVENT_TYPE_CITY_AREA_RESTORE = "city_area:restore"

    EVENT_TYPE_COMPANY_CREATE = "company:create"
    EVENT_TYPE_COMPANY_MODIFY = "company:update"
    EVENT_TYPE_COMPANY_ARCHIVE = "company:archive"
    EVENT_TYPE_COMPANY_RESTORE = "company:restore"
    EVENT_TYPE_COMPANY_LOGO_DELETE = "company:logo delete"
    EVENT_TYPE_COMPANY_PHOTO_CREATE = "company_photo:create"
    EVENT_TYPE_COMPANY_PHOTO_MODIFY = "company_photo:update"
    EVENT_TYPE_COMPANY_PHOTO_DELETE = "company_photo:delete"
    EVENT_TYPE_COMPANY_BASIC_INFO_UPDATE = "company:basic info update"
    EVENT_TYPE_COMPANY_CHANGE_PASSWORD = "company:password change"
    EVENT_TYPE_COMPANY_STATUS_UPDATE = "company:status update"

    EVENT_TYPE_PARTNER_COMPANY_CREATE = "partner_company:create"
    EVENT_TYPE_PARTNER_COMPANY_MODIFY = "partner_company:update"
    EVENT_TYPE_PARTNER_COMPANY_ARCHIVE = "partner_company:archive"
    EVENT_TYPE_PARTNER_COMPANY_RESTORE = "partner_company:restore"
    EVENT_TYPE_PARTNER_COMPANY_BASIC_INFO_UPDATE = "partner_company:basic info update"
    EVENT_TYPE_PARTNER_COMPANY_CHANGE_PASSWORD = "partner_company:password change"
    EVENT_TYPE_PARTNER_COMPANY_STATUS_UPDATE = "partner_company:status update"
    EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_CREATE = "partner_company_document:create"
    EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_MODIFY = "partner_company_document:update"
    EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_ARCHIVE = "partner_company_document:archive"
    EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_RESTORE = "partner_company_document:restore"

    EVENT_TYPE_END_CLIENT_CREATE = "endclient:create"
    EVENT_TYPE_END_CLIENT_MODIFY = "endclient:update"
    EVENT_TYPE_END_CLIENT_ARCHIVE = "endclient:archive"
    EVENT_TYPE_END_CLIENT_RESTORE = "endclient:restore"
    EVENT_TYPE_END_CLIENT_PHOTO_DELETE = "endclient:photo delete"
    EVENT_TYPE_END_CLIENT_BASIC_INFO_UPDATE = "endclient:basic info update"
    EVENT_TYPE_END_CLIENT_CHANGE_PASSWORD = "endclient:password change"
    EVENT_TYPE_END_CLIENT_STATUS_UPDATE = "endclient:status update"

    EVENT_TYPE_EMPLOYEE_CREATE = "employee:create"
    EVENT_TYPE_EMPLOYEE_MODIFY = "employee:update"
    EVENT_TYPE_EMPLOYEE_ARCHIVE = "employee:archive"
    EVENT_TYPE_EMPLOYEE_RESTORE = "employee:restore"

    EVENT_TYPE_COUNTRY_CREATE = "country:create"
    EVENT_TYPE_COUNTRY_MODIFY = "country:update"
    EVENT_TYPE_COUNTRY_ARCHIVE = "country:archive"
    EVENT_TYPE_COUNTRY_RESTORE = "country:restore"

    EVENT_TYPE_BUSINESS_CATEGORY_CREATE = "business_category:create"
    EVENT_TYPE_BUSINESS_CATEGORY_MODIFY = "business_category:update"
    EVENT_TYPE_BUSINESS_CATEGORY_ARCHIVE = "business_category:archive"
    EVENT_TYPE_BUSINESS_CATEGORY_RESTORE = "business_category:restore"

    EVENT_TYPE_NOTIFICATION_TEMPLATE_CREATE = "notification_template:create"
    EVENT_TYPE_NOTIFICATION_TEMPLATE_MODIFY = "notification_template:update"
    EVENT_TYPE_NOTIFICATION_TEMPLATE_ARCHIVE = "notification_template:archive"
    EVENT_TYPE_NOTIFICATION_TEMPLATE_RESTORE = "notification_template:restore"

    EVENT_TYPE_SITE_LOCATION_CREATE = "site_location:create"
    EVENT_TYPE_SITE_LOCATION_MODIFY = "site_location:update"
    EVENT_TYPE_SITE_LOCATION_ARCHIVE = "site_location:archive"
    EVENT_TYPE_SITE_LOCATION_RESTORE = "site_location:restore"

    EVENT_TYPE_QUOTATION_CREATE = "quotation:create"
    EVENT_TYPE_QUOTATION_MODIFY = "quotation:update"
    EVENT_TYPE_QUOTATION_ARCHIVE = "quotation:archive"
    EVENT_TYPE_QUOTATION_RESTORE = "quotation:restore"

    EVENT_TYPE_QUOTATION_DETAIL_CREATE = "quotation_detail:create"
    EVENT_TYPE_QUOTATION_DETAIL_MODIFY = "quotation_detail:update"
    EVENT_TYPE_QUOTATION_DETAIL_ARCHIVE = "quotation_detail:archive"
    EVENT_TYPE_QUOTATION_DETAIL_RESTORE = "quotation_detail:restore"

    EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_CREATE = "vendor_signed_document:create"
    EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_MODIFY = "vendor_signed_document:update"
    EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_ARCHIVE = "vendor_signed_document:archive"
    EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_RESTORE = "vendor_signed_document:restore"

    EVENT_TYPE_QUOTATION_QUERY_CREATE = "quotation_query:create"
    EVENT_TYPE_QUOTATION_QUERY_MODIFY = "quotation_query:update"
    EVENT_TYPE_QUOTATION_QUERY_ARCHIVE = "quotation_query:archive"
    EVENT_TYPE_QUOTATION_QUERY_RESTORE = "quotation_query:restore"

    EVENT_TYPE_REQUEST_DEMO_CREATE = "request_demo:create"
    EVENT_TYPE_REQUEST_DEMO_MODIFY = "request_demo:update"
    EVENT_TYPE_REQUEST_DEMO_ARCHIVE = "request_demo:archive"
    EVENT_TYPE_REQUEST_DEMO_RESTORE = "request_demo:restore"

    EVENT_TYPE_SUBSCRIPTION_CREATE = "subscription:create"
    EVENT_TYPE_SUBSCRIPTION_MODIFY = "subscription:update"
    EVENT_TYPE_SUBSCRIPTION_ARCHIVE = "subscription:archive"
    EVENT_TYPE_SUBSCRIPTION_RESTORE = "subscription:restore"

    EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE = "purchased_subscription:create"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY = "purchased_subscription:update"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE = "purchased_subscription:archive"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE = "purchased_subscription:restore"

    EVENT_TYPE_SUBSCRIPTION_FEATURE_CREATE = "subscription_feature:create"
    EVENT_TYPE_SUBSCRIPTION_FEATURE_MODIFY = "subscription_feature:update"
    EVENT_TYPE_SUBSCRIPTION_FEATURE_ARCHIVE = "subscription_feature:archive"
    EVENT_TYPE_SUBSCRIPTION_FEATURE_RESTORE = "subscription_feature:restore"

    EVENT_TYPE_SUBSCRIPTION_INVOICE_CREATE = "subscription_invoice:create"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_MODIFY = "subscription_invoice:update"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_ARCHIVE = "subscription_invoice:archive"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_RESTORE = "subscription_invoice:restore"

    EVENT_TYPE_BUSINESS_SETTING_MODIFY = "business_setting:update"

    EVENT_TYPE_FAQ_CREATE = "faq:create"
    EVENT_TYPE_FAQ_MODIFY = "faq:update"
    EVENT_TYPE_FAQ_ARCHIVE = "faq:archive"
    EVENT_TYPE_FAQ_RESTORE = "faq:restore"

    EVENT_TYPE_METER_CONFIG_CREATE = "meter_config:create"
    EVENT_TYPE_METER_CONFIG_MODIFY = "meter_config:update"
    EVENT_TYPE_METER_CONFIG_ARCHIVE = "meter_config:archive"
    EVENT_TYPE_METER_CONFIG_RESTORE = "meter_config:restore"

    EVENT_TYPE_DEVICE_CONFIGURATION_CREATE = "device_configuration:create"
    EVENT_TYPE_DEVICE_CONFIGURATION_MODIFY = "device_configuration:update"
    EVENT_TYPE_DEVICE_CONFIGURATION_ASSIGN = "device_configuration:assign"
    EVENT_TYPE_DEVICE_CONFIGURATION_EDIT_SITE = "device_configuration:edit_site"
    EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_STATUS = "device_configuration:update_status"
    EVENT_TYPE_DEVICE_CONFIGURATION_CREATE_SCHEDULE = "device_configuration:create_schedule"
    EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_SCHEDULE = "device_configuration:update_schedule"
    EVENT_TYPE_DEVICE_CONFIGURATION_POWER_CONTROL = "device_configuration:power_control"
    EVENT_TYPE_DEVICE_CONFIGURATION_ARCHIVE = "device_configuration:archive"
    EVENT_TYPE_DEVICE_CONFIGURATION_RESTORE = "device_configuration:restore"

    EVENT_TYPE_DEVICE_TRANSFER_CREATE = "device_transfer:create"
    EVENT_TYPE_DEVICE_TRANSFER_UPDATE = "device_transfer:update"
    EVENT_TYPE_DEVICE_TRANSFER_EDIT_REQUEST = "device_transfer:edit_request"
    EVENT_TYPE_DEVICE_TRANSFER_UPDATE_STATUS = "device_transfer:update_status"
    EVENT_TYPE_DEVICE_TRANSFER_ARCHIVE = "device_transfer:archive"
    EVENT_TYPE_DEVICE_TRANSFER_RESTORE = "device_transfer:restore"
    EVENT_TYPE_DEVICE_TRANSFER_SITE_PHOTO_DELETE = "device_transfer:site_photo_delete"

    EVENT_TYPE = (
        (EVENT_TYPE_STATE_CREATE, "Add State"),
        (EVENT_TYPE_STATE_MODIFY, "Modify State"),
        (EVENT_TYPE_STATE_ARCHIVE, "Archive State"),
        (EVENT_TYPE_STATE_RESTORE, "Restore State"),
        (EVENT_TYPE_CITY_CREATE, "Add City"),
        (EVENT_TYPE_CITY_MODIFY, "Modify City"),
        (EVENT_TYPE_CITY_ARCHIVE, "Archive City"),
        (EVENT_TYPE_CITY_RESTORE, "Restore City"),
        (EVENT_TYPE_CITY_AREA_CREATE, "Add City Area"),
        (EVENT_TYPE_CITY_AREA_MODIFY, "Modify City Area"),
        (EVENT_TYPE_CITY_AREA_ARCHIVE, "Archive City Area"),
        (EVENT_TYPE_CITY_AREA_RESTORE, "Restore City Area"),
        (EVENT_TYPE_COMPANY_CREATE, "Add Company"),
        (EVENT_TYPE_COMPANY_MODIFY, "Modify Company"),
        (EVENT_TYPE_COMPANY_ARCHIVE, "Archive Company"),
        (EVENT_TYPE_COMPANY_RESTORE, "Restore Company"),
        (EVENT_TYPE_COMPANY_LOGO_DELETE, "Company Logo Detele"),
        (EVENT_TYPE_COMPANY_PHOTO_CREATE, "Add Company Photo"),
        (EVENT_TYPE_COMPANY_PHOTO_MODIFY, "Modify Company Photo"),
        (EVENT_TYPE_COMPANY_PHOTO_DELETE, "Delete Company Photo"),
        (EVENT_TYPE_COMPANY_BASIC_INFO_UPDATE, "Company Basic Info Update"),
        (EVENT_TYPE_COMPANY_CHANGE_PASSWORD, "Company Password Change"),
        (EVENT_TYPE_COMPANY_STATUS_UPDATE, "Company Status Change"),
        (EVENT_TYPE_PARTNER_COMPANY_CREATE, "Add Partner Company"),
        (EVENT_TYPE_PARTNER_COMPANY_MODIFY, "Modify Partner Company"),
        (EVENT_TYPE_PARTNER_COMPANY_ARCHIVE, "Archive Partner Company"),
        (EVENT_TYPE_PARTNER_COMPANY_RESTORE, "Restore Partner Company"),
        (EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_CREATE, "Add Partner Company Document"),
        (EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_MODIFY, "Modify Partner Company Document"),
        (EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_ARCHIVE, "Archive Partner Company Document"),
        (EVENT_TYPE_PARTNER_COMPANY_DOCUMENT_RESTORE, "Restore Partner Company Document"),
        (EVENT_TYPE_PARTNER_COMPANY_BASIC_INFO_UPDATE, "Partner Company Basic Info Update"),
        (EVENT_TYPE_PARTNER_COMPANY_CHANGE_PASSWORD, "Partner Company Password Change"),
        (EVENT_TYPE_PARTNER_COMPANY_STATUS_UPDATE, "Partner Company Status Update"),
        (EVENT_TYPE_END_CLIENT_CREATE, "Add EndClient"),
        (EVENT_TYPE_END_CLIENT_MODIFY, "Modify EndClient"),
        (EVENT_TYPE_END_CLIENT_ARCHIVE, "Archive EndClient"),
        (EVENT_TYPE_END_CLIENT_RESTORE, "Restore EndClient"),
        (EVENT_TYPE_END_CLIENT_PHOTO_DELETE, "EndClient Photo Detele"),
        (EVENT_TYPE_END_CLIENT_BASIC_INFO_UPDATE, "EndClient Basic Info Update"),
        (EVENT_TYPE_END_CLIENT_CHANGE_PASSWORD, "EndClient Password Change"),
        (EVENT_TYPE_END_CLIENT_STATUS_UPDATE, "EndClient Status Change"),
        (EVENT_TYPE_EMPLOYEE_CREATE, "Add Employee"),
        (EVENT_TYPE_EMPLOYEE_MODIFY, "Modify Employee"),
        (EVENT_TYPE_EMPLOYEE_ARCHIVE, "Archive Employee"),
        (EVENT_TYPE_EMPLOYEE_RESTORE, "Restore Employee"),
        (EVENT_TYPE_COUNTRY_CREATE, "Add Country"),
        (EVENT_TYPE_COUNTRY_MODIFY, "Modify Country"),
        (EVENT_TYPE_COUNTRY_ARCHIVE, "Archive Country"),
        (EVENT_TYPE_COUNTRY_RESTORE, "Restore Country"),
        (EVENT_TYPE_BUSINESS_CATEGORY_CREATE, "Add Business Category"),
        (EVENT_TYPE_BUSINESS_CATEGORY_MODIFY, "Modify Business Category"),
        (EVENT_TYPE_BUSINESS_CATEGORY_ARCHIVE, "Archive Business Category"),
        (EVENT_TYPE_BUSINESS_CATEGORY_RESTORE, "Restore Business Category"),
        (EVENT_TYPE_NOTIFICATION_TEMPLATE_CREATE, "Add Notification Template"),
        (EVENT_TYPE_NOTIFICATION_TEMPLATE_MODIFY, "Modify Notification Template"),
        (EVENT_TYPE_NOTIFICATION_TEMPLATE_ARCHIVE, "Archive Notification Template"),
        (EVENT_TYPE_NOTIFICATION_TEMPLATE_RESTORE, "Restore Notification Template"),
        (EVENT_TYPE_SITE_LOCATION_CREATE, "Add Site location"),
        (EVENT_TYPE_SITE_LOCATION_MODIFY, "Modify Site location"),
        (EVENT_TYPE_SITE_LOCATION_ARCHIVE, "Archive Site location"),
        (EVENT_TYPE_SITE_LOCATION_RESTORE, "Restore Site location"),
        (EVENT_TYPE_QUOTATION_CREATE, "Add Quotation"),
        (EVENT_TYPE_QUOTATION_MODIFY, "Modify Quotation"),
        (EVENT_TYPE_QUOTATION_ARCHIVE, "Archive Quotation"),
        (EVENT_TYPE_QUOTATION_RESTORE, "Restore Quotation"),
        (EVENT_TYPE_QUOTATION_DETAIL_CREATE, "Add Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_MODIFY, "Modify Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_ARCHIVE, "Archive Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_RESTORE, "Restore Quotation Detail"),
        (EVENT_TYPE_QUOTATION_QUERY_CREATE, "Add Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_MODIFY, "Modify Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_ARCHIVE, "Archive Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_RESTORE, "Restore Quotation Query"),
        (EVENT_TYPE_REQUEST_DEMO_CREATE, "Add Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_MODIFY, "Modify Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_ARCHIVE, "Archive Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_RESTORE, "Restore Request Demo"),
        (EVENT_TYPE_SUBSCRIPTION_CREATE, "Add Subscription"),
        (EVENT_TYPE_SUBSCRIPTION_MODIFY, "Modify Subscription"),
        (EVENT_TYPE_SUBSCRIPTION_ARCHIVE, "Archive Subscription"),
        (EVENT_TYPE_SUBSCRIPTION_RESTORE, "Restore Subscription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE, "Add Purchased  Subscription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY, "Modify Purchased Subscription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE, "Archive Purchased Subscription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE, "Restore Purchased Subscription"),
        (EVENT_TYPE_SUBSCRIPTION_FEATURE_CREATE, "Add Subscription Feature"),
        (EVENT_TYPE_SUBSCRIPTION_FEATURE_MODIFY, "Modify Subscription Feature"),
        (EVENT_TYPE_SUBSCRIPTION_FEATURE_ARCHIVE, "Archive Subscription Feature"),
        (EVENT_TYPE_SUBSCRIPTION_FEATURE_RESTORE, "Restore Subscription Feature"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_CREATE, "Add Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_MODIFY, "Modify Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_ARCHIVE, "Archive Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_RESTORE, "Restore Subscription Invoice"),
        (EVENT_TYPE_BUSINESS_SETTING_MODIFY, "Modify Business Setting"),
        (EVENT_TYPE_FAQ_MODIFY, "Modify FAQ"),
        (EVENT_TYPE_FAQ_ARCHIVE, "Archive FAQ"),
        (EVENT_TYPE_FAQ_RESTORE, "Restore FAQ"),
        (EVENT_TYPE_METER_CONFIG_CREATE, "Add Meter Config"),
        (EVENT_TYPE_METER_CONFIG_MODIFY, "Modify Meter Config"),
        (EVENT_TYPE_METER_CONFIG_ARCHIVE, "Archive Meter Config"),
        (EVENT_TYPE_METER_CONFIG_RESTORE, "Restore Meter Config"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_CREATE, "Add Device Configuration"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_MODIFY, "Modify Device Configuration"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_ASSIGN, "Assign Device Configuration"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_EDIT_SITE, "Edit Device Configuration Site"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_STATUS, "Update Device Configuration Status"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_CREATE_SCHEDULE, "Create Device Configuration Schedule"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_UPDATE_SCHEDULE, "Update Device Configuration Schedule"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_POWER_CONTROL, "Device Configuration Power Control"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_ARCHIVE, "Archive Device Configuration"),
        (EVENT_TYPE_DEVICE_CONFIGURATION_RESTORE, "Restore Device Configuration"),
        (EVENT_TYPE_DEVICE_TRANSFER_CREATE, "Add Device Transfer"),
        (EVENT_TYPE_DEVICE_TRANSFER_UPDATE, "Update Device Transfer"),
        (EVENT_TYPE_DEVICE_TRANSFER_EDIT_REQUEST, "Edit Device Transfer Request"),
        (EVENT_TYPE_DEVICE_TRANSFER_UPDATE_STATUS, "Update Device Transfer Status"),
        (EVENT_TYPE_DEVICE_TRANSFER_ARCHIVE, "Archive Device Transfer"),
        (EVENT_TYPE_DEVICE_TRANSFER_RESTORE, "Restore Device Transfer"),
        (EVENT_TYPE_DEVICE_TRANSFER_SITE_PHOTO_DELETE, "Device Transfer Site Photo Delete"),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    company_photo = models.ForeignKey(CompanyPhoto, on_delete=models.CASCADE, null=True)
    partner_company = models.ForeignKey(PartnerCompany, on_delete=models.CASCADE, null=True)
    partner_company_document = models.ForeignKey(PartnerCompanyDocument, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
    state = models.ForeignKey("state.State", on_delete=models.CASCADE, null=True)
    city = models.ForeignKey("city.City", on_delete=models.CASCADE, null=True)
    city_area = models.ForeignKey(CityArea, on_delete=models.CASCADE, null=True)
    business_category = models.ForeignKey("business_category.BusinessCategory", on_delete=models.CASCADE, null=True)
    business_setting = models.ForeignKey(BusinessSetting, on_delete=models.CASCADE, null=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True)
    subscription_invoice = models.ForeignKey(SubscriptionInvoice, on_delete=models.CASCADE, null=True)
    subscription_feature = models.ForeignKey(SubscriptionFeature, on_delete=models.CASCADE, null=True)
    subscription_invoice = models.ForeignKey(SubscriptionInvoice, on_delete=models.CASCADE, null=True)
    faq = models.ForeignKey(FAQ, on_delete=models.CASCADE, null=True)
    end_client = models.ForeignKey(EndClient, on_delete=models.CASCADE, null=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE)
    details = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.CharField(null=True, max_length=100)

    objects = EventQuerySet.as_manager()

    def __str__(self):
        return f"{self.event_type} - {self.changed_at}"

    class Meta:
        ordering = ["-changed_at"]

    log = EventCreater()
