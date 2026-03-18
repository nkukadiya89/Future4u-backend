from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from base.api.responses import api_error, api_success
from company.api.serializers import CompanyCreateSerializer, CompanyReadSerializer
from company.services.onboarding_service import CompanyOnboardingService
from company.services.company_update_service import CompanyUpdateService
from company.selectors.company_selector import get_active_company_queryset
from utils.pagination import Pagination


class CompanyV1ViewSet(ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination

    def get_queryset(self):
        return get_active_company_queryset()

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return CompanyReadSerializer
        return CompanyCreateSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return api_success(data=serializer.data, message="Company list fetched")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return api_error(
                message="Validation failed",
                errors=serializer.errors,
                status_code=400,
                code="validation_error",
            )

        service = CompanyOnboardingService()
        company = service.execute(serializer.validated_data, actor=request.user)
        return api_success(
            data=CompanyReadSerializer(company).data,
            message="Company created successfully",
            status_code=201,
        )

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return api_success(data=serializer.data, message="Company fetched")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CompanyCreateSerializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_error(
                message="Validation failed",
                errors=serializer.errors,
                status_code=400,
                code="validation_error",
            )

        updated_company = CompanyUpdateService().execute(
            company=instance,
            validated_data=serializer.validated_data,
            actor=request.user,
        )
        return api_success(
            data=CompanyReadSerializer(updated_company).data,
            message="Company updated successfully",
        )
