from company.views import (
    CompanyArchiveViewSet,
    CompanyPhotoArchiveViewSet,
    CompanyPhotoRestoreViewSet,
    CompanyPhotoViewSet,
    CompanyRestoreViewSet,
    CompanyViewSet,
    CreateCompanyAccountViewSet,
    EnquiryViewSet,
    GovtDocumentVerification,
)
from rest_framework.routers import DefaultRouter

company_router = DefaultRouter()
company_router.register("company", CompanyViewSet, basename="company")
company_router.register(
    "company-archive", CompanyArchiveViewSet, basename="company_archive"
)
company_router.register(
    "company-restore", CompanyRestoreViewSet, basename="company_restore"
)
company_router.register("company-photo", CompanyPhotoViewSet, basename="company_photo")
company_router.register(
    "company-photo-archive",
    CompanyPhotoArchiveViewSet,
    basename="company_photo_archive",
)
company_router.register(
    "company-photo-restore",
    CompanyPhotoRestoreViewSet,
    basename="company_photo_restore",
)
company_router.register("enquiry", EnquiryViewSet, basename="enquiry")
company_router.register(
    "create-company-account",
    CreateCompanyAccountViewSet,
    basename="create_company_account",
)
company_router.register(
    "doc-verification", GovtDocumentVerification, basename="doc_verification"
)
