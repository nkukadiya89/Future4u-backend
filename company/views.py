import json
from datetime import datetime, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from company.models import Attachment, Company, CompanyEmail
from company.api.serializers import CompanyCreateSerializer
from company.serializer import (
    CompanyAttachmentArchiveSerializer,
    CompanyAttachmentRestoreSerializer,
    CompanyAttachmentSerializer,
    CompanyDeleteSerializer,
    CompanyInfoSerializer,
    CompanyRestoreSerializer,
    CompanyVerifyEmailNotificationsSerializer,
    VerifyEmailNotificationsInfoSerializer,
)
from company.selectors.company_selector import get_active_company_queryset
from company.services.company_update_service import CompanyUpdateService
from company.services.onboarding_service import CompanyOnboardingService
from subscription.models import PaymentSubscription, Subcription
from user.models import User
from utils.aws_file_upload import delete_uploaded_file
from utils.pagination import Pagination


class SearchOrderingFilter:
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "name",
        "website",
        "no_of_employees",
        "company_type",
        "company_pan",
        "gst_no",
        "about_company",
        "email",
        "phone",
        "first_name",
        "designation",
        "status",
        "is_active",
        "unique_code",
        "cin_no",
        "sector__sector_name",
        "company_logo",
        "risk_and_compliance_title",
        "udhyam_aadharcard",
        "registered_business_address_building",
        "registered_business_address_area",
        "registered_business_address_landmark",
        "registered_business_address_state",
        "registered_business_address_city",
        "registered_business_address_pincode__pincode_number",
        "trading_address_building",
        "trading_address_area",
        "trading_address_landmark",
        "trading_address_state",
        "trading_address_city",
        "trading_address_pincode__pincode_number",
        "key_person__person_name",
        "key_person__designation",
        "key_person__email",
        "key_person__contact_number",
        "key_person__department",
        "attachment__attachment_name",
        "attachment__attachment_file",
    ]

    ordering_fields = [
        "name",
        "website",
        "no_of_employees",
        "company_type",
        "company_pan",
        "gst_no",
        "about_company",
        "email",
        "phone",
        "first_name",
        "designation",
        "status",
        "is_active",
        "unique_code",
        "cin_no",
        "sector__sector_name",
        "company_logo",
        "risk_and_compliance_title",
        "udhyam_aadharcard",
        "registered_business_address_building",
        "registered_business_address_area",
        "registered_business_address_landmark",
        "registered_business_address_state",
        "registered_business_address_city",
        "registered_business_address_pincode__pincode_number",
        "trading_address_building",
        "trading_address_area",
        "trading_address_landmark",
        "trading_address_state",
        "trading_address_city",
        "trading_address_pincode__pincode_number",
        "key_person__person_name",
        "key_person__designation",
        "key_person__email",
        "key_person__contact_number",
        "key_person__department",
        "attachment__attachment_name",
        "attachment__attachment_file",
    ]


class CompanyViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = get_active_company_queryset()
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def _parse_create_payload(self, request):
        raw_form_data = request.data.get("form_data")
        if raw_form_data:
            return json.loads(raw_form_data)
        if hasattr(request.data, "dict"):
            return request.data.dict()
        return dict(request.data)

    def _create_welcome_subscription(self, company_instance):
        welcome_package = Subcription.objects.get(
            package_name="Welcome Package", status="active", deleted=0
        )
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=int(welcome_package.duration))  # type: ignore
        days_to_expire = (end_date - start_date).days

        PaymentSubscription.objects.create(
            company=company_instance,
            subscription=welcome_package,
            sell_price=welcome_package.sell_price,
            amount=0.0,
            duration=welcome_package.duration,
            start_date=start_date,
            end_date=end_date,
            active="Active",
            status="Active",
        )
        company_instance.expiry_date = end_date  # type: ignore
        company_instance.days_to_expire = days_to_expire  # type: ignore
        company_instance.save(update_fields=["expiry_date", "days_to_expire"])

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(get_active_company_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = CompanyInfoSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CompanyInfoSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        try:
            data = self._parse_create_payload(request)
        except (TypeError, ValueError, json.JSONDecodeError):
            return Response(
                {"success": False, "message": "Invalid form_data payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CompanyCreateSerializer(data=data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    company_instance = CompanyOnboardingService().execute(
                        serializer.validated_data,
                        actor=request.user,
                    )
                    self._create_welcome_subscription(company_instance)
            except Subcription.DoesNotExist:
                return Response(
                    {
                        "success": False,
                        "message": "Welcome Package not found in Subscription",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response_serializer = CompanyInfoSerializer(company_instance)
            return Response(
                {
                    "success": True,
                    "message": "Company created successfully",
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        errors_message = " ".join(
            [", ".join(value) for value in serializer.errors.values()]  # type: ignore
        )
        return Response(
            {"success": False, "message": errors_message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            data = self._parse_create_payload(request)
        except (TypeError, ValueError, json.JSONDecodeError):
            return Response(
                {"success": False, "message": "Invalid form_data payload"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = CompanyCreateSerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            updated_company = CompanyUpdateService().execute(
                company=instance,
                validated_data=serializer.validated_data,
                actor=request.user,
            )
            response_serializer = CompanyInfoSerializer(updated_company)
            return Response(
                {"success": True, "data": response_serializer.data},
                status=status.HTTP_200_OK,
            )

        errors_message = " ".join(
            [", ".join(value) for value in serializer.errors.values()]
        )
        return Response(
            {"success": False, "errors": errors_message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CompanyInfoSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Company Delete"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="company-logo-delete")
    def company_logo_delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.company_logo:
            delete_uploaded_file(instance.company_logo)
            instance.company_logo = None
            instance.save()
            return Response(
                {"success": True, "message": "Company Logo Deleted Successfully."},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": "Company Logo Not Found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_path="company-basic-info")
    def get_company_basic_info(self, request, pk=None):
        try:
            company = Company.objects.get(id=pk, deleted=0)

            data = {
                "company_logo": company.company_logo,
                "first_name": company.first_name,
                "email": company.email,
                "phone": company.phone,
            }
            return Response(data, status=200)

        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=404)

    @action(detail=True, methods=["PATCH"], url_path="update-company-person")
    def update_company_person(self, request, pk=None):
        try:
            company = Company.objects.get(id=pk)
            form_data = json.loads(request.data.get("form_data", "{}"))
            first_name = form_data.get("first_name")
            phone = form_data.get("phone")
            company_logo = request.data.get("company_logo", None)

            # Update Company Model
            if first_name:
                company.first_name = first_name
            if phone:
                company.phone = phone
            if company_logo:
                company.upload_company_logo_presentation(company_logo)

            company.updated_by = request.user
            company.save()

            users = User.objects.filter(company=company)
            for user in users:
                if first_name:
                    user.first_name = first_name
                if phone:
                    user.phone = phone
                user.save()

            return Response(
                {"message": "Company details updated successfully."}, status=200
            )

        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=404)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON in form_data."}, status=400)

    @action(detail=True, methods=["PATCH"], url_path="change-company-password")
    def change_company_password(self, request, pk=None):
        try:
            company = Company.objects.get(id=pk)
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")
            re_enter_password = request.data.get("re_enter_password")

            if not (old_password and new_password and re_enter_password):
                return Response({"error": "All fields are required."}, status=400)

            if new_password != re_enter_password:
                return Response(
                    {"error": "New password and Re-enter password do not match."},
                    status=400,
                )

            user = User.objects.filter(company=company, role="Company Admin").first()

            if not user:
                return Response(
                    {"error": "Admin user not found for this company."}, status=404
                )

            if not check_password(old_password, user.password):
                return Response({"error": "Current password is incorrect."}, status=400)

            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()

            return Response({"message": "Password updated successfully."}, status=200)

        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=404)


# Company Multiple Deleted
class CompanyDeleteViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Company.objects.filter(deleted=0).order_by("-id")
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = CompanyDeleteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Company archive Succefully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": True, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Company Multiple Restore
class CompanyRestoreViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Company.objects.filter(deleted=1).order_by("id")
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = CompanyRestoreSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Company restore Succefully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CompanyAttachmentViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Attachment.objects.filter(deleted=0).order_by("-id")
    serializer_class = CompanyAttachmentSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["attachment_name", "attachment_file"]
    ordering_fields = ["attachment_name", "attachment_file"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(
                queryset, many=True, context={"request": request}
            )
            return Response({"success": True, "data": serializer.data})

        if page:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data},
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            instance = serializer.save()

            company_attachment = Attachment.objects.filter(
                company=instance.company  # type: ignore
            )
            serializer = CompanyAttachmentSerializer(company_attachment, many=True)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"succcess": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        attachment_id = kwargs.get("pk")
        instance = self.queryset.get(pk=attachment_id)

        data = json.loads(request.data["form_data"])
        data["updated_by"] = request.user.id
        attachment_file = request.data.get("attachment_file", None)
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()

            if attachment_file:
                instance.upload_company_attachment_presentation(attachment_file)
                instance.save()

            company_attachment = Attachment.objects.filter(company=instance.company)
            serializer = CompanyAttachmentSerializer(company_attachment, many=True)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Attachmnet Deleted Success"},
            status=status.HTTP_200_OK,
        )

    # Company Image Delete
    @action(detail=True, methods=["delete"], url_path="company-attachment-delete")
    def company_attachment_delete(self, request, *args, **kwargs):
        instance = self.get_object()
        attachment_file = instance.attachment_file

        if attachment_file:
            instance.attachment_file = None
            instance.save()
            return Response(
                {"success": True, "message": "Image deleted"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": "Image not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CompanyAttachmentArchiveViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Attachment.objects.filter(deleted=0).order_by("-id")
    serializer_class = CompanyAttachmentSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["attachment_name", "attachment_file"]
    ordering_fields = ["attachment_name", "attachment_file"]

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = CompanyAttachmentArchiveSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Company Attachemnt Arhcive success"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CompanyAttachmentRestoreViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Attachment.objects.filter(deleted=1).order_by("-id")
    serializer_class = CompanyAttachmentSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["attachment_name", "attachment_file"]
    ordering_fields = ["attachment_name", "attachment_file"]

    def get_queryset(self):
        queryset = Attachment.objects.filter(deleted=1).order_by("-id")

        company_id = self.request.query_params.get("company_id")  # type: ignore
        if company_id:
            queryset = queryset.filter(company=company_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")

        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CompanyAttachmentRestoreSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Comapany Attchemnt Restore"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Company ID to Document
class CompanyAttachmentByIdViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Attachment.objects.filter(deleted=0).order_by("-id")
    serializer_class = CompanyAttachmentSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    search_fields = ["attachment_name", "attachment_file"]
    ordering_fields = ["attachment_name", "attachment_file"]

    def list(self, request, args, *kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        self.pagination_class.page_size = int(request.query_params.get("pagesize", 10))
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(
                queryset, many=True, context={"request": request}
            )
            return Response({"success": True, "data": serializer.data})

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def retrieve(self, request, *args, **kwargs):
        company_id = self.kwargs.get("pk")
        queryset = Attachment.objects.filter(deleted=0, company_id=company_id)

        search_param = request.query_params.get("search", "")
        if search_param and len(search_param) >= 2:
            queryset = queryset.filter(attachment_name__startswith=search_param)

        ordering_param = request.query_params.get("ordering", "id")
        queryset = queryset.order_by(ordering_param)

        serializer = self.serializer_class(queryset, many=True)

        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )


# Company Email ViewSet :
class CompanyVerifyEmailNotificationsSerializerViewSet(ModelViewSet):
    queryset = CompanyEmail.objects.filter(deleted=0).order_by("-id")
    serializer_class = CompanyVerifyEmailNotificationsSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "company__name",
        "email",
        "person_name",
        "designation",
        "phone_number",
    ]

    ordering_filter = [
        "company__name",
        "email",
        "person_name",
        "designation",
        "phone_number",
    ]

    def list(self, request, *args, **kwargs):
        company_id = self.request.query_params.get("company_id")  # type: ignore

        if company_id:
            queryset = self.filter_queryset(
                CompanyEmail.objects.filter(company=company_id).order_by("-id")
            )
            self.pagination_class.page_size = int(
                request.query_params.get("pagesize", 10)
            )
            page = self.paginate_queryset(queryset)
            no_pagination = request.query_params.get("no_pagination")

            if no_pagination:
                serializer = self.serializer_class(queryset, many=True)
                return Response({"success": True, "data": serializer.data})

            if page is not None:
                serializer = VerifyEmailNotificationsInfoSerializer(queryset, many=True)
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = VerifyEmailNotificationsInfoSerializer(page, many=True)
            return Response({"success": True, "data": serializer.data})

        else:
            if page is not None:  # type: ignore
                serializer = VerifyEmailNotificationsInfoSerializer(
                    queryset, many=True  # type: ignore
                )
                return self.get_paginated_response(
                    {"success": True, "data": serializer.data}
                )

            serializer = VerifyEmailNotificationsInfoSerializer(page, many=True)
            return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data, context={"request": request})

        if serializer.is_valid():
            with transaction.atomic():
                instance = serializer.save()
                response_serializer = VerifyEmailNotificationsInfoSerializer(
                    instance, many=True
                )

                return Response(
                    {"success": True, "data": response_serializer.data},
                    status=status.HTTP_201_CREATED,
                )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        company_id = self.kwargs.get("pk")
        try:
            instance = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {"sucess": False, "message": "Company Not Found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = request.data
        data["updated_by"] = request.user.id
        serializer = self.serializer_class(
            instance, data=data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            with transaction.atomic():
                instance = serializer.save()
                response_serializer = VerifyEmailNotificationsInfoSerializer(
                    instance, many=True
                )
                return Response(
                    {"success": True, "data": response_serializer.data},
                    status=status.HTTP_200_OK,
                )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Company Email Deleted SuccessFully."},
            status=status.HTTP_200_OK,
        )
