from django.conf import settings
from django.db import models
from django.utils.timezone import now

from company.models import Company
from country.models import Country
from currency.models import Currency
from pincode.models import PinCode
from subscription.models import (Subcription, SubscriptionFeature,
                                 SubscriptionInvoice)
from user.models import User


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
    def company_create(company, ip_address, user=None):
        details = f"{company.name} - {user.email}"  # type: ignore
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_CREATE,
            company=company,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_update(company, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_MODIFY,
            company=company,
            user=user,
            details=details,
        )

    @staticmethod
    def company_archive(company, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_ARCHIVE,
            company=company,
            user=user,
            details=details,
        )

    @staticmethod
    def company_restore(company, user):
        details = f"{company.name} - {user.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_RESTORE,
            company=company,
            user=user,
            details=details,
        )

    # Vendor
    @staticmethod
    def vendor_create(vendor, ip_address, user=None):
        details = f"{vendor.person_name} - {vendor.email} - {vendor.designation}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_VENDOR_CREATE,
            vendor=vendor,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def vendor_modify(vendor, user):
        details = f"{vendor.person_name} - {vendor.email} - {vendor.designation}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_VENDOR_MODIFY,
            vendor=vendor,
            user=user,
            details=details,
        )

    @staticmethod
    def vendor_archive(vendor, user):
        details = f"{vendor.person_name} - {vendor.email} - {vendor.designation}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_VENDOR_ARCHIVE,
            vendor=vendor,
            user=user,
            details=details,
        )

    @staticmethod
    def vendor_restore(vendor, user):
        details = f"{vendor.person_name} - {vendor.email} - {vendor.designation}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_VENDOR_RESTORE,
            vendor=vendor,
            user=user,
            details=details,
        )

    # Employee
    @staticmethod
    def employee_create(employee, ip_address, user=None, company=None):
        details = f"{employee.employe_id} - {employee.first_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_CREATE,
            employee=employee,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def employee_modify(employee, user, company=None):
        details = f"{employee.employe_id} - {employee.first_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_MODIFY,
            employee=employee,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def employee_archive(employee, user=None, company=None):
        details = f"{employee.employe_id} - {employee.first_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_ARCHIVE,
            employee=employee,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def employee_restore(employee, user=None, company=None):
        details = f"{employee.employe_id} - {employee.first_name} - {employee.email}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_EMPLOYEE_RESTORE,
            employee=employee,
            user=user,
            details=details,
            company=company,
        )

    # Category Tree
    @staticmethod
    def category_tree_create(category_tree, ip_address, user=None):
        details = (
            f"{category_tree.name} - {category_tree.description} - "
            f"{category_tree.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CATEGORY_TREE_CREATE,
            category_tree=category_tree,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def category_tree_update(category_tree, user):
        details = (
            f"{category_tree.name} - {category_tree.description} - "
            f"{category_tree.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CATEGORY_TREE_MODIFY,
            category_tree=category_tree,
            user=user,
            details=details,
        )

    @staticmethod
    def category_tree_archive(category_tree, user):
        details = (
            f"{category_tree.name} - {category_tree.description} - "
            f"{category_tree.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CATEGORY_TREE_ARCHIVE,
            category_tree=category_tree,
            user=user,
            details=details,
        )

    @staticmethod
    def category_tree_restore(category_tree, user):
        details = (
            f"{category_tree.name} - {category_tree.description} - "
            f"{category_tree.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CATEGORY_TREE_RESTORE,
            category_tree=category_tree,
            user=user,
            details=details,
        )

    # Company_document
    @staticmethod
    def company_document_create(company_document, ip_address, user=None):
        details = f"{company_document.company} - {company_document.document_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_DOCUMENT_CREATE,
            company_document=company_document,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def company_document_modify(company_document, user):
        details = f"{company_document.company} - {company_document.document_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_DOCUMENT_MODIFY,
            company_document=company_document,
            user=user,
            details=details,
        )

    @staticmethod
    def company_document_archive(company_document, user):
        details = f"{company_document.company} - {company_document.document_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_DOCUMENT_ARCHIVE,
            company_document=company_document,
            user=user,
            details=details,
        )

    @staticmethod
    def company_document_restore(company_document, user):
        details = f"{company_document.company} - {company_document.document_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_COMPANY_DOCUMENT_RESTORE,
            company_document=company_document,
            user=user,
            details=details,
        )

    # country
    @staticmethod
    def country_create(country, ip_address, user=None):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_CREATE,
            country=country,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def country_update(country, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_MODIFY,
            country=country,
            user=user,
            details=details,
        )

    @staticmethod
    def country_archive(country, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_ARCHIVE,
            country=country,
            user=user,
            details=details,
        )

    @staticmethod
    def country_restore(country, user):
        details = f"{country.name} - {country.code} - {country.unicode}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_RESTORE,
            country=country,
            user=user,
            details=details,
        )

    # Currency
    @staticmethod
    def currency_create(currency, ip_address, user=None):
        details = (
            f"{currency.country} - {currency.currency_name} - {currency.currency_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_CREATE,
            currency=currency,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def currency_modify(currency, user):
        details = (
            f"{currency.country} - {currency.currency_name} - {currency.currency_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_MODIFY,
            currency=currency,
            user=user,
            details=details,
        )

    @staticmethod
    def currency_archive(currency, user):
        details = (
            f"{currency.country} - {currency.currency_name} - {currency.currency_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_ARCHIVE,
            currency=currency,
            user=user,
            details=details,
        )

    @staticmethod
    def currency_restore(currency, user):
        details = (
            f"{currency.country} - {currency.currency_name} - {currency.currency_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_CURRENCY_RESTORE,
            currency=currency,
            user=user,
            details=details,
        )

    # delivery address
    @staticmethod
    def delivery_address_create(delivery_address, ip_address, user=None):
        details = (
            f"{delivery_address.state} - {delivery_address.city} - "
            f"{delivery_address.address_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DELIVERY_ADDRESS_CREATE,
            delivery_address=delivery_address,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def delivery_address_modify(delivery_address, user):
        details = (
            f"{delivery_address.state} - {delivery_address.city} - "
            f"{delivery_address.address_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DELIVERY_ADDRESS_MODIFY,
            delivery_address=delivery_address,
            user=user,
            details=details,
        )

    @staticmethod
    def delivery_address_archive(delivery_address, user):
        details = (
            f"{delivery_address.state} - {delivery_address.city} - "
            f"{delivery_address.address_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DELIVERY_ADDRESS_ARCHIVE,
            delivery_address=delivery_address,
            user=user,
            details=details,
        )

    @staticmethod
    def delivery_address_restore(delivery_address, user):
        details = (
            f"{delivery_address.state} - {delivery_address.city} - "
            f"{delivery_address.address_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_DELIVERY_ADDRESS_RESTORE,
            delivery_address=delivery_address,
            user=user,
            details=details,
        )

    # Material Master
    @staticmethod
    def material_master_create(material_master, ip_address, user=None):
        details = (
            f"{material_master.category_tree} - {material_master.material_type} - "
            f"{material_master.code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_MASTER_CREATE,
            material_master=material_master,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def material_master_update(material_master, user):
        details = (
            f"{material_master.category_tree} - {material_master.material_type} - "
            f"{material_master.code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_MASTER_MODIFY,
            material_master=material_master,
            user=user,
            details=details,
        )

    @staticmethod
    def material_master_archive(material_master, user):
        details = (
            f"{material_master.category_tree} - {material_master.material_type} - "
            f"{material_master.code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_MASTER_ARCHIVE,
            material_master=material_master,
            user=user,
            details=details,
        )

    @staticmethod
    def material_master_restore(material_master, user):
        details = (
            f"{material_master.category_tree} - {material_master.material_type} - "
            f"{material_master.code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_MASTER_RESTORE,
            material_master=material_master,
            user=user,
            details=details,
        )

    # Material Type
    @staticmethod
    def material_type_create(material_type, ip_address, user=None):
        details = (
            f"{material_type.category_tree} - {material_type.type_name} - "
            f"{material_type.hsn_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_TYPE_CREATE,
            material_type=material_type,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def material_type_modify(material_type, user):
        details = (
            f"{material_type.category_tree} - {material_type.type_name} - "
            f"{material_type.hsn_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_TYPE_MODIFY,
            material_type=material_type,
            user=user,
            details=details,
        )

    @staticmethod
    def material_type_archive(material_type, user):
        details = (
            f"{material_type.category_tree} - {material_type.type_name} - "
            f"{material_type.hsn_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_TYPE_ARCHIVE,
            material_type=material_type,
            user=user,
            details=details,
        )

    @staticmethod
    def material_type_restore(material_type, user):
        details = (
            f"{material_type.category_tree} - {material_type.type_name} - "
            f"{material_type.hsn_code}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_MATERIAL_TYPE_RESTORE,
            material_type=material_type,
            user=user,
            details=details,
        )

    # Pincode
    @staticmethod
    def pincode_create(pincode, ip_address, user=None):
        details = f"{pincode.zone_id} - {pincode.pincode_number}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PINCODE_CREATE,
            pincode=pincode,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def pincode_update(pincode, user):
        details = f"{pincode.zone_id} - {pincode.pincode_number}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PINCODE_MODIFY,
            pincode=pincode,
            user=user,
            details=details,
        )

    @staticmethod
    def pincode_archive(pincode, user):
        details = f"{pincode.zone_id} - {pincode.pincode_number}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PINCODE_ARCHIVE,
            pincode=pincode,
            user=user,
            details=details,
        )

    @staticmethod
    def pincode_restore(pincode, user):
        details = f"{pincode.zone_id} - {pincode.pincode_number}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PINCODE_RESTORE,
            pincode=pincode,
            user=user,
            details=details,
        )

    # Request DEmo
    @staticmethod
    def request_demo_create(request_demo, ip_address, user=None):
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

    # RFQ
    @staticmethod
    def rfq_create(rfq, ip_address, user=None):
        details = f"{rfq.approve} - {rfq.rfq_number} - {rfq.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_CREATE,
            rfq=rfq,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def rfq_update(rfq, user):
        details = f"{rfq.approve} - {rfq.rfq_number} - {rfq.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_MODIFY,
            rfq=rfq,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_archive(rfq, user):
        details = f"{rfq.approve} - {rfq.rfq_number} - {rfq.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_ARCHIVE,
            rfq=rfq,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_restore(rfq, user):
        details = f"{rfq.approve} - {rfq.rfq_number} - {rfq.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_RESTORE,
            rfq=rfq,
            user=user,
            details=details,
        )

    # RFQ Detail
    @staticmethod
    def rfq_detail_create(rfq_detail, ip_address, user=None):
        details = (
            f"{rfq_detail.rfq} - {rfq_detail.category} - {rfq_detail.material_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DETAIL_CREATE,
            rfq_detail=rfq_detail,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def rfq_detail_update(rfq_detail, user):
        details = (
            f"{rfq_detail.rfq} - {rfq_detail.category} - {rfq_detail.material_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DETAIL_MODIFY,
            rfq_detail=rfq_detail,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_detail_archive(rfq_detail, user):
        details = (
            f"{rfq_detail.rfq} - {rfq_detail.category} - {rfq_detail.material_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DETAIL_ARCHIVE,
            rfq_detail=rfq_detail,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_detail_restore(rfq_detail, user):
        details = (
            f"{rfq_detail.rfq} - {rfq_detail.category} - {rfq_detail.material_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DETAIL_RESTORE,
            rfq_detail=rfq_detail,
            user=user,
            details=details,
        )

    # RFQ Document

    @staticmethod
    def rfq_documents_create(rfq_documents, ip_address, user=None):
        details = (
            f"{rfq_documents.document_type} - {rfq_documents.document_name} - "
            f"{rfq_documents.material}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DOCUMENTS_CREATE,
            rfq_documents=rfq_documents,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def rfq_documents_modify(rfq_documents, user):
        details = (
            f"{rfq_documents.document_type} - {rfq_documents.document_name} - "
            f"{rfq_documents.material}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DOCUMENTS_MODIFY,
            rfq_documents=rfq_documents,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_documents_archive(rfq_documents, user):
        details = (
            f"{rfq_documents.document_type} - {rfq_documents.document_name} - "
            f"{rfq_documents.material}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DOCUMENTS_ARCHIVE,
            rfq_documents=rfq_documents,
            user=user,
            details=details,
        )

    @staticmethod
    def rfq_documents_restore(rfq_documents, user):
        details = (
            f"{rfq_documents.document_type} - {rfq_documents.document_name} - "
            f"{rfq_documents.material}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_RFQ_DOCUMENTS_RESTORE,
            rfq_documents=rfq_documents,
            user=user,
            details=details,
        )

    # Subscrpiton

    @staticmethod
    def subcription_create(subcription, ip_address, user=None):
        details = (
            f"{subcription.package_name} - {subcription.subscription_type} - "
            f"{subcription.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_CREATE,
            subcription=subcription,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subcription_update(subcription, user):
        details = (
            f"{subcription.package_name} - {subcription.subscription_type} - "
            f"{subcription.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_MODIFY,
            subcription=subcription,
            user=user,
            details=details,
        )

    @staticmethod
    def subcription_archive(subcription, user):
        details = (
            f"{subcription.package_name} - {subcription.subscription_type} - "
            f"{subcription.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_ARCHIVE,
            subcription=subcription,
            user=user,
            details=details,
        )

    @staticmethod
    def subcription_restore(subcription, user):
        details = (
            f"{subcription.package_name} - {subcription.subscription_type} - "
            f"{subcription.status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_RESTORE,
            subcription=subcription,
            user=user,
            details=details,
        )

    # Purchased subscription
    @staticmethod
    def subscription_invoice_create(subscription_invoice, ip_address, user=None):
        details = (
            f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subscription_invoice_update(subscription_invoice, user):
        details = (
            f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
        )

    @staticmethod
    def subscription_invoice_archive(subscription_invoice, user):
        details = (
            f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
        )

    @staticmethod
    def subscription_invoice_restore(subscription_invoice, user):
        details = (
            f"{subscription_invoice.subscription} - {subscription_invoice.company}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE,
            subscription_invoice=subscription_invoice,
            user=user,
            details=details,
        )

    # SUBCRIPTION Feature
    @staticmethod
    def subcription_feature_create(subcription_feature, ip_address, user=None):
        details = (
            f"{subcription_feature.subscription} - {subcription_feature.feature_name} - "
            f"{subcription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_FEATURE_CREATE,
            subcription_feature=subcription_feature,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def subcription_feature_update(subcription_feature, user):
        details = (
            f"{subcription_feature.subscription} - {subcription_feature.feature_name} - "
            f"{subcription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_FEATURE_MODIFY,
            subcription_feature=subcription_feature,
            user=user,
            details=details,
        )

    @staticmethod
    def subcription_feature_archive(subcription_feature, user):
        details = (
            f"{subcription_feature.subscription} - {subcription_feature.feature_name} - "
            f"{subcription_feature.feature_status}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_FEATURE_ARCHIVE,
            subcription_feature=subcription_feature,
            user=user,
            details=details,
        )

    @staticmethod
    def subcription_feature_restore(subcription_feature, user):
        details = (
            f"{subcription_feature.subscription} - {subcription_feature.feature_name} - "
            f"{subcription_feature.feature_status_type}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SUBCRIPTION_FEATURE_RESTORE,
            subcription_feature=subcription_feature,
            user=user,
            details=details,
        )

    @staticmethod
    def zone_name_create(zone_name, ip_address, user=None):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ZONE_NAME_CREATE,
            zone_name=zone_name,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def zone_name_update(zone_name, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ZONE_NAME_MODIFY,
            zone_name=zone_name,
            user=user,
            details=details,
        )

    @staticmethod
    def zone_name_archive(zone_name, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ZONE_NAME_ARCHIVE,
            zone_name=zone_name,
            user=user,
            details=details,
        )

    @staticmethod
    def zone_name_restore(zone_name, user):
        details = f"{zone_name.zone_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ZONE_NAME_RESTORE,
            zone_name=zone_name,
            user=user,
            details=details,
        )

    # UNIT OF MEASUREMENT
    @staticmethod
    def unit_of_measurement_create(unit_of_measurement, ip_address, user=None):
        details = f"{unit_of_measurement.unit_of_measurement}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_UNIT_OF_MEASUREMENT_CREATE,
            unit_of_measurement=unit_of_measurement,
            ip_address=ip_address,
            user=user,
            details=details,
        )

    @staticmethod
    def unit_of_measurement_update(unit_of_measurement, user):
        details = f"{unit_of_measurement.unit_of_measurement}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_UNIT_OF_MEASUREMENT_MODIFY,
            unit_of_measurement=unit_of_measurement,
            user=user,
            details=details,
        )

    @staticmethod
    def unit_of_measurement_archive(unit_of_measurement, user):
        details = f"{unit_of_measurement.unit_of_measurement}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_UNIT_OF_MEASUREMENT_ARCHIVE,
            unit_of_measurement=unit_of_measurement,
            user=user,
            details=details,
        )

    @staticmethod
    def unit_of_measurement_restore(unit_of_measurement, user):
        details = f"{unit_of_measurement.unit_of_measurement}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_UNIT_OF_MEASUREMENT_RESTORE,
            unit_of_measurement=unit_of_measurement,
            user=user,
            details=details,
        )

    # Address Master
    @staticmethod
    def address_master_create(address_master, ip_address, user=None, company=None):
        details = (
            f"{address_master.company_legal_name} - {address_master.site_name} - "
            f"{address_master.gst_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ADDRESS_MASTER_CREATE,
            address_master=address_master,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def address_master_modify(address_master, user=None, company=None):
        details = (
            f"{address_master.company_legal_name} - {address_master.site_name} - "
            f"{address_master.gst_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ADDRESS_MASTER_MODIFY,
            address_master=address_master,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def address_master_archive(address_master, user=None, company=None):
        details = (
            f"{address_master.company_legal_name} - {address_master.site_name} - "
            f"{address_master.gst_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ADDRESS_MASTER_ARCHIVE,
            address_master=address_master,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def address_master_restore(address_master, user=None, company=None):
        details = (
            f"{address_master.company_legal_name} - {address_master.site_name} - "
            f"{address_master.gst_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_ADDRESS_MASTER_RESTORE,
            address_master=address_master,
            user=user,
            details=details,
            company=company,
        )

    # Purchase Requisition Master
    @staticmethod
    def purchase_requisition_create(purchase_requisition, ip_address, user=None):
        details = (
            f"{purchase_requisition.category_tree} - {purchase_requisition.company}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASE_REQUISITION_CREATE,
            purchase_requisition=purchase_requisition,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def purchase_requisition_modify(purchase_requisition, user):
        details = (
            f"{purchase_requisition.category_tree} - {purchase_requisition.company} "
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASE_REQUISITION_MODIFY,
            purchase_requisition=purchase_requisition,
            user=user,
            details=details,
        )

    @staticmethod
    def purchase_requisition_archive(purchase_requisition, user):
        details = (
            f"{purchase_requisition.category_tree} - {purchase_requisition.company} "
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASE_REQUISITION_ARCHIVE,
            purchase_requisition=purchase_requisition,
            user=user,
            details=details,
        )

    @staticmethod
    def purchase_requisition_restore(purchase_requisition, user):
        details = (
            f"{purchase_requisition.category_tree} - {purchase_requisition.company} "
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PURCHASE_REQUISITION_RESTORE,
            purchase_requisition=purchase_requisition,
            user=user,
            details=details,
        )

    # Sector name

    @staticmethod
    def sector_name_create(sector_name, ip_address, user=None):
        details = f"{sector_name.sector_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SECTOR_NAME_CREATE,
            sector_name=sector_name,
            user=user,
            details=details,
            ip_address=ip_address,
        )

    @staticmethod
    def sector_name_update(sector_name, user):
        details = f"{sector_name.sector_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SECTOR_NAME_MODIFY,
            sector_name=sector_name,
            user=user,
            details=details,
        )

    @staticmethod
    def sector_name_archive(sector_name, user):
        details = f"{sector_name.sector_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SECTOR_NAME_ARCHIVE,
            sector_name=sector_name,
            user=user,
            details=details,
        )

    @staticmethod
    def sector_name_restore(sector_name, user):
        details = f"{sector_name.sector_name}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_SECTOR_NAME_RESTORE,
            sector_name=sector_name,
            user=user,
            details=details,
        )

    # Business Setting

    @staticmethod
    def business_setting_update(business_setting, user, company=None):
        details = (
            f"{business_setting.company} - {business_setting.currency} - "
            f"{business_setting.buying_pattern}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_BUSINESS_SETTING_MODIFY,
            business_setting=business_setting,
            user=user,
            details=details,
            company=company,
        )

    # PR Release
    @staticmethod
    def pr_release_create(pr_release, ip_address, user=None, company=None):
        details = f"{pr_release.address_master} - {pr_release.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PR_RELEASE_CREATE,
            pr_release=pr_release,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def pr_release_modify(pr_release, user, company=None):
        details = f"{pr_release.address_master} - {pr_release.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PR_RELEASE_MODIFY,
            pr_release=pr_release,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def pr_release_archive(pr_release, user=None, company=None):
        details = f"{pr_release.address_master} - {pr_release.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PR_RELEASE_ARCHIVE,
            pr_release=pr_release,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def pr_release_restore(pr_release, user=None, company=None):
        details = f"{pr_release.address_master} - {pr_release.company}"
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_PR_RELEASE_RESTORE,
            pr_release=pr_release,
            user=user,
            details=details,
            company=company,
        )

    # Float RFQ
    @staticmethod
    def float_rfq_create(float_rfq, ip_address, user=None, company=None):
        details = (
            f"{float_rfq.company} - {float_rfq.category_tree} - {float_rfq.rfq_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FLOAT_RFQ_CREATE,
            float_rfq=float_rfq,
            user=user,
            details=details,
            ip_address=ip_address,
            company=company,
        )

    @staticmethod
    def float_rfq_modify(float_rfq, user, company=None):
        details = (
            f"{float_rfq.company} - {float_rfq.category_tree} - {float_rfq.rfq_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FLOAT_RFQ_MODIFY,
            float_rfq=float_rfq,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def float_rfq_archive(float_rfq, user=None, company=None):
        details = (
            f"{float_rfq.company} - {float_rfq.category_tree} - {float_rfq.rfq_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FLOAT_RFQ_ARCHIVE,
            float_rfq=float_rfq,
            user=user,
            details=details,
            company=company,
        )

    @staticmethod
    def float_rfq_restore(float_rfq, user=None, company=None):
        details = (
            f"{float_rfq.company} - {float_rfq.category_tree} - {float_rfq.rfq_number}"
        )
        return ActivityLog.objects.create(
            event_type=ActivityLog.EVENT_TYPE_FLOAT_RFQ_RESTORE,
            float_rfq=float_rfq,
            user=user,
            details=details,
            company=company,
        )

    # Bid RFQ
    @staticmethod
    def bid_rfq_create(bid_rfqs, user=None, vendor=None):
        for bid_rfq in bid_rfqs:
            details = (
                f"{bid_rfq.id} - {bid_rfq.rfq_material_detail} -  "
                f"{bid_rfq.is_final_bid_price}"
            )
            return ActivityLog.objects.create(
                event_type=ActivityLog.EVENT_TYPE_BID_RFQ_CREATE,
                bid_rfq=bid_rfq,
                user=user,
                details=details,
                vendor=vendor,
            )

    @staticmethod
    def bid_rfq_modify(bid_rfqs, user=None, vendor=None):
        for bid_rfq in bid_rfqs:
            details = (
                f"{bid_rfq.vendor} - {bid_rfq.rfq_vendor_detail} - "
                f"{bid_rfq.is_final_bid_price}"
            )
            return ActivityLog.objects.create(
                event_type=ActivityLog.EVENT_TYPE_BID_RFQ_MODIFY,
                bid_rfq=bid_rfq,
                user=user,
                details=details,
                vendor=vendor,
            )


class ActivityLog(models.Model):
    EVENT_TYPE_COMPANY_CREATE = "company:create"
    EVENT_TYPE_COMPANY_MODIFY = "company:update"
    EVENT_TYPE_COMPANY_ARCHIVE = "company:archive"
    EVENT_TYPE_COMPANY_RESTORE = "company:restore"

    EVENT_TYPE_VENDOR_CREATE = "vendor:create"
    EVENT_TYPE_VENDOR_MODIFY = "vendor:update"
    EVENT_TYPE_VENDOR_ARCHIVE = "vendor:archive"
    EVENT_TYPE_VENDOR_RESTORE = "vendor:restore"

    EVENT_TYPE_EMPLOYEE_CREATE = "employee:create"
    EVENT_TYPE_EMPLOYEE_MODIFY = "employee:update"
    EVENT_TYPE_EMPLOYEE_ARCHIVE = "employee:archive"
    EVENT_TYPE_EMPLOYEE_RESTORE = "employee:restore"

    EVENT_TYPE_CATEGORY_TREE_CREATE = "category_tree:create"
    EVENT_TYPE_CATEGORY_TREE_MODIFY = "category_tree:update"
    EVENT_TYPE_CATEGORY_TREE_ARCHIVE = "category_tree:archive"
    EVENT_TYPE_CATEGORY_TREE_RESTORE = "category_tree:restore"

    EVENT_TYPE_COMPANY_DOCUMENT_CREATE = "company_document:create"
    EVENT_TYPE_COMPANY_DOCUMENT_MODIFY = "company_document:update"
    EVENT_TYPE_COMPANY_DOCUMENT_ARCHIVE = "company_document:archive"
    EVENT_TYPE_COMPANY_DOCUMENT_RESTORE = "company_document:restore"

    EVENT_TYPE_COUNTRY_CREATE = "country:create"
    EVENT_TYPE_COUNTRY_MODIFY = "country:update"
    EVENT_TYPE_COUNTRY_ARCHIVE = "country:archive"
    EVENT_TYPE_COUNTRY_RESTORE = "country:restore"

    EVENT_TYPE_CURRENCY_CREATE = "currency:create"
    EVENT_TYPE_CURRENCY_MODIFY = "currency:update"
    EVENT_TYPE_CURRENCY_ARCHIVE = "currency:archive"
    EVENT_TYPE_CURRENCY_RESTORE = "currency:restore"

    EVENT_TYPE_DELIVERY_ADDRESS_CREATE = "delivery_address:create"
    EVENT_TYPE_DELIVERY_ADDRESS_MODIFY = "delivery_address:update"
    EVENT_TYPE_DELIVERY_ADDRESS_ARCHIVE = "delivery_address:archive"
    EVENT_TYPE_DELIVERY_ADDRESS_RESTORE = "delivery_address:restore"

    EVENT_TYPE_MATERIAL_MASTER_CREATE = "material_master:create"
    EVENT_TYPE_MATERIAL_MASTER_MODIFY = "material_master:update"
    EVENT_TYPE_MATERIAL_MASTER_ARCHIVE = "material_master:archive"
    EVENT_TYPE_MATERIAL_MASTER_RESTORE = "material_master:restore"

    EVENT_TYPE_MATERIAL_TYPE_CREATE = "material_type:create"
    EVENT_TYPE_MATERIAL_TYPE_MODIFY = "material_type:update"
    EVENT_TYPE_MATERIAL_TYPE_ARCHIVE = "material_type:archive"
    EVENT_TYPE_MATERIAL_TYPE_RESTORE = "material_type:restore"

    EVENT_TYPE_PINCODE_CREATE = "pincode:create"
    EVENT_TYPE_PINCODE_MODIFY = "pincode:update"
    EVENT_TYPE_PINCODE_ARCHIVE = "pincode:archive"
    EVENT_TYPE_PINCODE_RESTORE = "pincode:restore"

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

    EVENT_TYPE_RFQ_CREATE = "rfq:create"
    EVENT_TYPE_RFQ_MODIFY = "rfq:update"
    EVENT_TYPE_RFQ_ARCHIVE = "rfq:archive"
    EVENT_TYPE_RFQ_RESTORE = "rfq:restore"

    EVENT_TYPE_RFQ_DETAIL_CREATE = "rfq_detail:create"
    EVENT_TYPE_RFQ_DETAIL_MODIFY = "rfq_detail:update"
    EVENT_TYPE_RFQ_DETAIL_ARCHIVE = "rfq_detail:archive"
    EVENT_TYPE_RFQ_DETAIL_RESTORE = "rfq_detail:restore"

    EVENT_TYPE_RFQ_DOCUMENTS_CREATE = "rfq_documents:create"
    EVENT_TYPE_RFQ_DOCUMENTS_MODIFY = "rfq_documents:update"
    EVENT_TYPE_RFQ_DOCUMENTS_ARCHIVE = "rfq_documents:archive"
    EVENT_TYPE_RFQ_DOCUMENTS_RESTORE = "rfq_documents:restore"

    EVENT_TYPE_SUBCRIPTION_CREATE = "subcription:create"
    EVENT_TYPE_SUBCRIPTION_MODIFY = "subcription:update"
    EVENT_TYPE_SUBCRIPTION_ARCHIVE = "subcription:archive"
    EVENT_TYPE_SUBCRIPTION_RESTORE = "subcription:restore"

    EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE = "purchased_subcription:create"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY = "purchased_subcription:update"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE = "purchased_subcription:archive"
    EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE = "purchased_subcription:restore"

    EVENT_TYPE_SUBCRIPTION_FEATURE_CREATE = "subcription_feature:create"
    EVENT_TYPE_SUBCRIPTION_FEATURE_MODIFY = "subcription_feature:update"
    EVENT_TYPE_SUBCRIPTION_FEATURE_ARCHIVE = "subcription_feature:archive"
    EVENT_TYPE_SUBCRIPTION_FEATURE_RESTORE = "subcription_feature:restore"

    EVENT_TYPE_SUBSCRIPTION_INVOICE_CREATE = "subscription_invoice:create"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_MODIFY = "subscription_invoice:update"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_ARCHIVE = "subscription_invoice:archive"
    EVENT_TYPE_SUBSCRIPTION_INVOICE_RESTORE = "subscription_invoice:restore"

    EVENT_TYPE_ZONE_NAME_CREATE = "zone_name:create"
    EVENT_TYPE_ZONE_NAME_MODIFY = "zone_name:update"
    EVENT_TYPE_ZONE_NAME_ARCHIVE = "zone_name:archive"
    EVENT_TYPE_ZONE_NAME_RESTORE = "zone_name:restore"

    EVENT_TYPE_UNIT_OF_MEASUREMENT_CREATE = "unit_of_measurement:create"
    EVENT_TYPE_UNIT_OF_MEASUREMENT_MODIFY = "unit_of_measurement:update"
    EVENT_TYPE_UNIT_OF_MEASUREMENT_ARCHIVE = "unit_of_measurement:archive"
    EVENT_TYPE_UNIT_OF_MEASUREMENT_RESTORE = "unit_of_measurement:restore"

    EVENT_TYPE_ADDRESS_MASTER_CREATE = "address_master:create"
    EVENT_TYPE_ADDRESS_MASTER_MODIFY = "address_master:update"
    EVENT_TYPE_ADDRESS_MASTER_ARCHIVE = "address_master:archive"
    EVENT_TYPE_ADDRESS_MASTER_RESTORE = "address_master:restore"

    EVENT_TYPE_PURCHASE_REQUISITION_CREATE = "purchase_requisition:create"
    EVENT_TYPE_PURCHASE_REQUISITION_MODIFY = "purchase_requisition:update"
    EVENT_TYPE_PURCHASE_REQUISITION_ARCHIVE = "purchase_requisition:archive"
    EVENT_TYPE_PURCHASE_REQUISITION_RESTORE = "purchase_requisition:restore"

    EVENT_TYPE_SECTOR_NAME_CREATE = "sector_name:create"
    EVENT_TYPE_SECTOR_NAME_MODIFY = "sector_name:update"
    EVENT_TYPE_SECTOR_NAME_ARCHIVE = "sector_name:archive"
    EVENT_TYPE_SECTOR_NAME_RESTORE = "sector_name:restore"

    EVENT_TYPE_BUSINESS_SETTING_MODIFY = "business_setting:update"

    EVENT_TYPE_PR_RELEASE_CREATE = "pr_release:create"
    EVENT_TYPE_PR_RELEASE_MODIFY = "pr_release:update"
    EVENT_TYPE_PR_RELEASE_ARCHIVE = "pr_release:archive"
    EVENT_TYPE_PR_RELEASE_RESTORE = "pr_release:restore"

    EVENT_TYPE_FLOAT_RFQ_CREATE = "float_rfq:create"
    EVENT_TYPE_FLOAT_RFQ_MODIFY = "float_rfq:update"
    EVENT_TYPE_FLOAT_RFQ_ARCHIVE = "float_rfq:archive"
    EVENT_TYPE_FLOAT_RFQ_RESTORE = "float_rfq:restore"

    EVENT_TYPE_BID_RFQ_CREATE = "bid_rfq:create"
    EVENT_TYPE_BID_RFQ_MODIFY = "bid_rfq:update"
    # EVENT_TYPE_BID_RFQ_ARCHIVE = "bid_rfq:archive"
    # EVENT_TYPE_BID_RFQ_RESTORE = "bid_rfq:restore"

    # EVENT_TYPE_CATEGORY_ITEM_SETTING_CREATE = "category_item_setting:create"
    # EVENT_TYPE_CATEGORY_ITEM_SETTING_MODIFY = "category_item_setting:update"

    EVENT_TYPE = (
        (EVENT_TYPE_COMPANY_CREATE, "Add Company"),
        (EVENT_TYPE_COMPANY_MODIFY, "Modify Company"),
        (EVENT_TYPE_COMPANY_ARCHIVE, "Archive Company"),
        (EVENT_TYPE_COMPANY_RESTORE, "Restore Company"),
        (EVENT_TYPE_VENDOR_CREATE, "Add Vendor"),
        (EVENT_TYPE_VENDOR_MODIFY, "Modify Vendor"),
        (EVENT_TYPE_VENDOR_ARCHIVE, "Archive Vendor"),
        (EVENT_TYPE_VENDOR_RESTORE, "Restore Vendor"),
        (EVENT_TYPE_EMPLOYEE_CREATE, "Add Employee"),
        (EVENT_TYPE_EMPLOYEE_MODIFY, "Modify Employee"),
        (EVENT_TYPE_EMPLOYEE_ARCHIVE, "Archive Employee"),
        (EVENT_TYPE_EMPLOYEE_RESTORE, "Restore Employee"),
        (EVENT_TYPE_CATEGORY_TREE_CREATE, "Add Category Tree"),
        (EVENT_TYPE_CATEGORY_TREE_MODIFY, "Modify Category Tree"),
        (EVENT_TYPE_CATEGORY_TREE_ARCHIVE, "Archive Category Tree"),
        (EVENT_TYPE_CATEGORY_TREE_RESTORE, "Restore Category Tree"),
        (EVENT_TYPE_COMPANY_DOCUMENT_CREATE, "Add Company document"),
        (EVENT_TYPE_COMPANY_DOCUMENT_MODIFY, "Modify Company document"),
        (EVENT_TYPE_COMPANY_DOCUMENT_ARCHIVE, "Archive Company document"),
        (EVENT_TYPE_COMPANY_DOCUMENT_RESTORE, "Restore Company document"),
        (EVENT_TYPE_COUNTRY_CREATE, "Add Country"),
        (EVENT_TYPE_COUNTRY_MODIFY, "Modify Country"),
        (EVENT_TYPE_COUNTRY_ARCHIVE, "Archive Country"),
        (EVENT_TYPE_COUNTRY_RESTORE, "Restore Country"),
        (EVENT_TYPE_CURRENCY_CREATE, "Add Currency"),
        (EVENT_TYPE_CURRENCY_MODIFY, "Modify Currency"),
        (EVENT_TYPE_CURRENCY_ARCHIVE, "Archive Currency"),
        (EVENT_TYPE_CURRENCY_RESTORE, "Restore Currency"),
        (EVENT_TYPE_DELIVERY_ADDRESS_CREATE, "Add Delivery address"),
        (EVENT_TYPE_DELIVERY_ADDRESS_MODIFY, "Modify Delivery address"),
        (EVENT_TYPE_DELIVERY_ADDRESS_ARCHIVE, "Archive Delivery address"),
        (EVENT_TYPE_DELIVERY_ADDRESS_RESTORE, "Restore Delivery address"),
        (EVENT_TYPE_MATERIAL_MASTER_CREATE, "Add Material master"),
        (EVENT_TYPE_MATERIAL_MASTER_MODIFY, "Modify Material master"),
        (EVENT_TYPE_MATERIAL_MASTER_ARCHIVE, "Archive Material master"),
        (EVENT_TYPE_MATERIAL_MASTER_RESTORE, "Restore Material master"),
        (EVENT_TYPE_MATERIAL_TYPE_CREATE, "Add Material Type"),
        (EVENT_TYPE_MATERIAL_TYPE_MODIFY, "Modify Material Type"),
        (EVENT_TYPE_MATERIAL_TYPE_ARCHIVE, "Archive Material Type"),
        (EVENT_TYPE_MATERIAL_TYPE_RESTORE, "Restore Material Type"),
        (EVENT_TYPE_PINCODE_CREATE, "Add Pincode"),
        (EVENT_TYPE_PINCODE_MODIFY, "Modify Pincode"),
        (EVENT_TYPE_PINCODE_ARCHIVE, "Archive Pincode"),
        (EVENT_TYPE_PINCODE_RESTORE, "Restore Pincode"),
        (EVENT_TYPE_QUOTATION_CREATE, "Add Quotation"),
        (EVENT_TYPE_QUOTATION_MODIFY, "Modify Quotation"),
        (EVENT_TYPE_QUOTATION_ARCHIVE, "Archive Quotation"),
        (EVENT_TYPE_QUOTATION_RESTORE, "Restore Quotation"),
        (EVENT_TYPE_QUOTATION_DETAIL_CREATE, "Add Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_MODIFY, "Modify Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_ARCHIVE, "Archive Quotation Detail"),
        (EVENT_TYPE_QUOTATION_DETAIL_RESTORE, "Restore Quotation Detail"),
        (EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_CREATE, "Add Vendor Signed Document"),
        (EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_MODIFY, "Modify Vendor Signed Document"),
        (EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_ARCHIVE, "Archive Vendor Signed Document"),
        (EVENT_TYPE_VENDOR_SIGNED_DOCUMENT_RESTORE, "Restore Vendor Signed Document"),
        (EVENT_TYPE_QUOTATION_QUERY_CREATE, "Add Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_MODIFY, "Modify Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_ARCHIVE, "Archive Quotation Query"),
        (EVENT_TYPE_QUOTATION_QUERY_RESTORE, "Restore Quotation Query"),
        (EVENT_TYPE_REQUEST_DEMO_CREATE, "Add Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_MODIFY, "Modify Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_ARCHIVE, "Archive Request Demo"),
        (EVENT_TYPE_REQUEST_DEMO_RESTORE, "Restore Request Demo"),
        (EVENT_TYPE_RFQ_CREATE, "Add Rfq Master"),
        (EVENT_TYPE_RFQ_MODIFY, "Modify Rfq Master"),
        (EVENT_TYPE_RFQ_ARCHIVE, "Archive Rfq Master"),
        (EVENT_TYPE_RFQ_RESTORE, "Restore Rfq Master"),
        (EVENT_TYPE_RFQ_DETAIL_CREATE, "Add Rfq Detail"),
        (EVENT_TYPE_RFQ_DETAIL_MODIFY, "Modify Rfq Detail"),
        (EVENT_TYPE_RFQ_DETAIL_ARCHIVE, "Archive Rfq Detail"),
        (EVENT_TYPE_RFQ_DETAIL_RESTORE, "Restore Rfq Detail"),
        (EVENT_TYPE_RFQ_DOCUMENTS_CREATE, "Add Rfq Documents"),
        (EVENT_TYPE_RFQ_DOCUMENTS_MODIFY, "Modify Rfq Documents"),
        (EVENT_TYPE_RFQ_DOCUMENTS_ARCHIVE, "Archive Rfq Documents"),
        (EVENT_TYPE_RFQ_DOCUMENTS_RESTORE, "Restore Rfq Documents"),
        (EVENT_TYPE_SUBCRIPTION_CREATE, "Add Subcription"),
        (EVENT_TYPE_SUBCRIPTION_MODIFY, "Modify Subcription"),
        (EVENT_TYPE_SUBCRIPTION_ARCHIVE, "Archive Subcription"),
        (EVENT_TYPE_SUBCRIPTION_RESTORE, "Restore Subcription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_CREATE, "Add Purchased  Subcription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_MODIFY, "Modify Purchased Subcription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_ARCHIVE, "Archive Purchased Subcription"),
        (EVENT_TYPE_PURCHASED_SUBSCRIPTION_RESTORE, "Restore Purchased Subcription"),
        (EVENT_TYPE_SUBCRIPTION_FEATURE_CREATE, "Add Subcription Feature"),
        (EVENT_TYPE_SUBCRIPTION_FEATURE_MODIFY, "Modify Subcription Feature"),
        (EVENT_TYPE_SUBCRIPTION_FEATURE_ARCHIVE, "Archive Subcription Feature"),
        (EVENT_TYPE_SUBCRIPTION_FEATURE_RESTORE, "Restore Subcription Feature"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_CREATE, "Add Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_MODIFY, "Modify Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_ARCHIVE, "Archive Subscription Invoice"),
        (EVENT_TYPE_SUBSCRIPTION_INVOICE_RESTORE, "Restore Subscription Invoice"),
        (EVENT_TYPE_ZONE_NAME_CREATE, "Add Zone Name"),
        (EVENT_TYPE_ZONE_NAME_MODIFY, "Modify Zone Name"),
        (EVENT_TYPE_ZONE_NAME_ARCHIVE, "Archive Zone Name"),
        (EVENT_TYPE_ZONE_NAME_RESTORE, "Restore Zone Name"),
        (EVENT_TYPE_UNIT_OF_MEASUREMENT_CREATE, "Add Unit of measurement"),
        (EVENT_TYPE_UNIT_OF_MEASUREMENT_MODIFY, "Modify Unit of measurement"),
        (EVENT_TYPE_UNIT_OF_MEASUREMENT_ARCHIVE, "Archive Unit of measurement"),
        (EVENT_TYPE_UNIT_OF_MEASUREMENT_RESTORE, "Restore Unit of measurement"),
        (EVENT_TYPE_ADDRESS_MASTER_CREATE, "Add Address Master"),
        (EVENT_TYPE_ADDRESS_MASTER_MODIFY, "Modify Address Master"),
        (EVENT_TYPE_ADDRESS_MASTER_ARCHIVE, "Archive Address Master"),
        (EVENT_TYPE_ADDRESS_MASTER_RESTORE, "Restore Address Master"),
        (EVENT_TYPE_PURCHASE_REQUISITION_CREATE, "Add Purchase Requisition"),
        (EVENT_TYPE_PURCHASE_REQUISITION_MODIFY, "Modify Purchase Requisition"),
        (EVENT_TYPE_PURCHASE_REQUISITION_ARCHIVE, "Archive Purchase Requisition"),
        (EVENT_TYPE_PURCHASE_REQUISITION_RESTORE, "Restore Purchase Requisition"),
        (EVENT_TYPE_BUSINESS_SETTING_MODIFY, "Modify Business Setting"),
        (EVENT_TYPE_PR_RELEASE_CREATE, "Add PR Release"),
        (EVENT_TYPE_PR_RELEASE_MODIFY, "Modify PR Release"),
        (EVENT_TYPE_PR_RELEASE_ARCHIVE, "Archive PR Release"),
        (EVENT_TYPE_PR_RELEASE_RESTORE, "Restore PR Release"),
        (EVENT_TYPE_FLOAT_RFQ_CREATE, "Add Float RFQ"),
        (EVENT_TYPE_FLOAT_RFQ_MODIFY, "Modify Float RFQ"),
        (EVENT_TYPE_FLOAT_RFQ_ARCHIVE, "Archive Float RFQ"),
        (EVENT_TYPE_FLOAT_RFQ_RESTORE, "Restore Float RFQ"),
        (EVENT_TYPE_BID_RFQ_CREATE, "Add Bid RFQ"),
        (EVENT_TYPE_BID_RFQ_MODIFY, "Modify Bid RFQ"),
        # (EVENT_TYPE_BID_RFQ_ARCHIVE, "Archive Bid RFQ"),
        # (EVENT_TYPE_BID_RFQ_RESTORE, "Restore Bid RFQ"),
        # (EVENT_TYPE_CATEGORY_ITEM_SETTING_CREATE, "Add Category Item Setting"),
        # (EVENT_TYPE_CATEGORY_ITEM_SETTING_MODIFY, "Modify Category Item Setting"),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True)
    pincode = models.ForeignKey(PinCode, on_delete=models.CASCADE, null=True)
    subcription = models.ForeignKey(Subcription, on_delete=models.CASCADE, null=True)
    subscription_invoice = models.ForeignKey(
        SubscriptionInvoice, on_delete=models.CASCADE, null=True
    )
    subcription_feature = models.ForeignKey(
        SubscriptionFeature, on_delete=models.CASCADE, null=True
    )
    subscription_invoice = models.ForeignKey(
        SubscriptionInvoice, on_delete=models.CASCADE, null=True
    )
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

    log = EventCreater()
    log = EventCreater()
    log = EventCreater()
    log = EventCreater()
    log = EventCreater()
