from partner_company.views import (
    PartnerCompanyArchiveViewSet,
    PartnerCompanyDocumentArchiveViewSet,
    PartnerCompanyDocumentRestoreViewSet,
    PartnerCompanyDocumentViewSet,
    PartnerCompanyRestoreViewSet,
    PartnerCompanyViewSet,
)
from rest_framework.routers import DefaultRouter

partner_company_router = DefaultRouter()
partner_company_router.register("partner-company", PartnerCompanyViewSet, basename="partner_company")
partner_company_router.register("partner-company-archive", PartnerCompanyArchiveViewSet, basename="partner_company_archive")
partner_company_router.register("partner-company-restore", PartnerCompanyRestoreViewSet, basename="partner_company_restore")
partner_company_router.register("partner-company-document", PartnerCompanyDocumentViewSet, basename="partner_company_document")
partner_company_router.register("partner-company-document-archive", PartnerCompanyDocumentArchiveViewSet, basename="partner_company_document_archive")
partner_company_router.register("partner-company-document-restore", PartnerCompanyDocumentRestoreViewSet, basename="partner_company_document_restore")
