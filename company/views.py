import json
import threading

from decouple import config
from django.contrib.auth.hashers import make_password
from django.db import models, transaction
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from common.mixins.view_mixins import (
    CreatePasswordEmailMixin,
    MethodNotAllowedListMixin,
)
from company.models import Company, CompanyPhoto, Enquiry
from company.serializers import (
    CompanyArchiveListSerializer,
    CompanyArchiveSerializer,
    CompanyInfoSerializer,
    CompanyPhotoArchiveSerializer,
    CompanyPhotoRestoreSerializer,
    CompanyPhotoSerializer,
    CompanyRestoreSerializer,
    CompanySerializer,
    CreateCompanySerializer,
    EnquirySerializer,
)
from email_utils.send_email import generate_forget_pass_token, send_mail
from user.models import CustomGroup, User
from utils.aws_file_upload import delete_uploaded_file
from utils.document_verification import GovernmentDocVerification
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class SearchOrderingFilter:
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "name",
        "company_type",
        "gst_no",
        "email",
        "phone",
        "person_name",
        "status",
        "is_active",
        "business_category__business_category",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "company_logo",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
        "secondary_email",
        "secondary_phone",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
        "instagram_url",
        "youtube_url",
        "pinterest_url",
        "year_of_establishment",
        "number_of_employees",
        "monday_friday_hours",
        "saturday_hours",
        "sunday_hours",
    ]

    ordering_fields = [
        "name",
        "company_type",
        "gst_no",
        "email",
        "phone",
        "person_name",
        "status",
        "is_active",
        "business_category__business_category",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "company_logo",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
        "secondary_email",
        "secondary_phone",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
        "instagram_url",
        "youtube_url",
        "pinterest_url",
        "year_of_establishment",
        "number_of_employees",
        "monday_friday_hours",
        "saturday_hours",
        "sunday_hours",
        "created_at",
        "updated_at",
    ]


class CompanyPhotoArchivedQuerysetMixin:
    def get_queryset(self):
        company_id = self.request.query_params.get("company_id")

        if company_id:
            try:
                company = Company.objects.get(id=company_id)
                return CompanyPhoto.objects.filter(
                    deleted=True, company=company
                ).order_by("-id")
            except Company.DoesNotExist:
                return CompanyPhoto.objects.none()
        elif self.request.user.company:
            return CompanyPhoto.objects.filter(
                deleted=True, company=self.request.user.company
            ).order_by("-id")
        else:
            return CompanyPhoto.objects.none()


class CreateCompanyAccountViewSet(CreatePasswordEmailMixin, viewsets.ViewSet):
    queryset = Company.objects.all()
    serializer_class = CreateCompanySerializer
    permission_classes = []
    authentication_classes = []

    def create(self, request):
        try:
            data = request.data
            serializer = CreateCompanySerializer(
                data=data, context={"request": request}
            )
            if serializer.is_valid(raise_exception=True):
                with transaction.atomic():
                    company = serializer.save()

                    email = serializer.validated_data.get("email")
                    user_phone = serializer.validated_data.get("phone")
                    name = serializer.validated_data.get("person_name")

                    if email and user_phone and name:
                        token = generate_forget_pass_token(email, user_phone, 30)

                        context = {"name": name, "token": token, "email": email}

                        try:
                            from user.models import CustomGroup

                            admin_group = CustomGroup.objects.filter(
                                name="Company Admin", company=company
                            ).first()
                            if admin_group:
                                user = (
                                    User.objects.filter(groups=admin_group)
                                    .order_by("id")
                                    .first()
                                )
                            else:
                                user = (
                                    User.objects.filter(
                                        groups__customgroup__company=company
                                    )
                                    .order_by("id")
                                    .first()
                                )

                            email_thread = threading.Thread(
                                target=self.send_email, args=(user, context)
                            )
                            email_thread.start()

                            message = (
                                "Company account created successfully. "
                                "Reset Password Mail has been sent to registered email"
                            )
                        except Exception:
                            message = "Company account created successfully but there was an error sending the email."
                    else:
                        message = "Company account created successfully"

                    return Response(
                        {
                            "status": True,
                            "message": message,
                            "data": CreateCompanySerializer(company).data,
                        },
                        status=status.HTTP_201_CREATED,
                    )
            return Response(
                {
                    "status": False,
                    "message": "Invalid data provided",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CompanyViewSet(CreatePasswordEmailMixin, SearchOrderingFilter, ModelViewSet):
    queryset = Company.objects.filter(deleted=False).order_by("-id")
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        state = request.query_params.get("state")
        city = request.query_params.get("city")
        city_area = request.query_params.get("city_area")
        company_type = request.query_params.get("company_type")

        if state:
            queryset = queryset.filter(
                models.Q(gst_address_state=state)
                | models.Q(communication_address_state=state)
            )

        if city:
            queryset = queryset.filter(
                models.Q(gst_address_city=city)
                | models.Q(communication_address_city=city)
            )

        if city_area:
            queryset = queryset.filter(
                models.Q(gst_address_area=city_area)
                | models.Q(communication_address_area=city_area)
            )

        if company_type:
            queryset = queryset.filter(models.Q(company_type=company_type))

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
        data = json.loads(request.data["form_data"])

        company_logo = request.data.get("company_logo")

        serializer = CompanySerializer(data=data, context={"request": request})

        if serializer.is_valid():
            with transaction.atomic():
                instance = serializer.save()

                ip_address = get_client_ip(request)
                ActivityLog.log.company_create(instance, ip_address, request.user)

                serializer = CompanyInfoSerializer(instance)
                email = data["email"]
                user_phone = data["phone"]
                name = data["person_name"]

                if company_logo and hasattr(company_logo, "read"):
                    instance.upload_company_logo_presentation(company_logo)
                    instance.save()

                instance.save()

                token = generate_forget_pass_token(email, user_phone, 30)

                context = {"name": name, "token": token, "email": email}

                admin_group = CustomGroup.objects.filter(
                    name="Company Admin", company=instance
                ).first()
                if admin_group:
                    user = (
                        User.objects.filter(groups=admin_group)
                        .order_by("id")
                        .first()
                    )
                else:
                    user = (
                        User.objects.filter(
                            groups__customgroup__company=instance
                        )
                        .order_by("id")
                        .first()
                    )

                email_thread = threading.Thread(
                    target=self.send_email, args=(user, context)
                )
                email_thread.start()
                return Response(
                    {
                        "success": True,
                        "message": (
                            "Reset Password Mail has been sent to registered email"
                        ),
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            errors = []
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    for error in error_list:
                        if isinstance(error, dict):
                            for nested_field, nested_error in error.items():
                                if isinstance(nested_error, list):
                                    errors.extend(
                                        [
                                            f"{field}.{nested_field}: {err}"
                                            for err in nested_error
                                        ]
                                    )
                                else:
                                    errors.append(
                                        f"{field}.{nested_field}: {nested_error}"
                                    )
                        else:
                            errors.append(f"{field}: {error}")
                elif isinstance(error_list, dict):
                    for nested_field, nested_error in error_list.items():
                        if isinstance(nested_error, list):
                            errors.extend(
                                [
                                    f"{field}.{nested_field}: {err}"
                                    for err in nested_error
                                ]
                            )
                        else:
                            errors.append(f"{field}.{nested_field}: {nested_error}")
                else:
                    errors.append(f"{field}: {error_list}")

            errors_message = " ".join(errors) if errors else "Validation failed"

            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = json.loads(request.data["form_data"])
        company_logo = request.data.get("company_logo")

        serializer = CompanySerializer(
            instance, data=data, context={"request": request}, partial=True
        )

        if serializer.is_valid():
            company = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.company_update(company, ip_address, request.user)

            if company_logo and hasattr(company_logo, "read"):
                instance.upload_company_logo_presentation(company_logo)
                instance.save()

            serializer = CompanyInfoSerializer(company)
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            errors = []
            for field, error_list in serializer.errors.items():
                if isinstance(error_list, list):
                    for error in error_list:
                        if isinstance(error, dict):
                            for nested_field, nested_error in error.items():
                                if isinstance(nested_error, list):
                                    errors.extend(
                                        [
                                            f"{field}.{nested_field}: {err}"
                                            for err in nested_error
                                        ]
                                    )
                                else:
                                    errors.append(
                                        f"{field}.{nested_field}: {nested_error}"
                                    )
                        else:
                            errors.append(f"{field}: {error}")
                elif isinstance(error_list, dict):
                    for nested_field, nested_error in error_list.items():
                        if isinstance(nested_error, list):
                            errors.extend(
                                [
                                    f"{field}.{nested_field}: {err}"
                                    for err in nested_error
                                ]
                            )
                        else:
                            errors.append(f"{field}.{nested_field}: {nested_error}")
                else:
                    errors.append(f"{field}: {error_list}")

            errors_message = " ".join(errors) if errors else "Validation failed"

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
        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()

        ip_address = get_client_ip(request)
        ActivityLog.log.company_archive(instance, ip_address, request.user)

        return Response(
            {"success": True, "message": "Company Delete"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="company-logo-delete")
    def company_logo_delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.company_logo:
            delete_uploaded_file(instance.company_logo)
            instance.company_logo = None
            instance.updated_by = request.user
            instance.updated_at = now()
            instance.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.company_logo_delete(instance, ip_address, request.user)
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
            company = Company.objects.get(id=pk, deleted=False)

            serializer = CompanySerializer(company)
            data = serializer.data

            return Response(data, status=200)

        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=404)

    @action(detail=True, methods=["PATCH"], url_path="update-company-basic-info")
    def update_company_basic_info(self, request, pk=None):
        try:
            company = Company.objects.get(id=pk)
            form_data = json.loads(request.data.get("form_data", "{}"))

            company_name = form_data.get("company_name")
            person_name = form_data.get("person_name")
            email = form_data.get("email")
            phone = form_data.get("phone")
            gst_no = form_data.get("gst_no")

            gst_address_country = form_data.get("gst_address_country")
            gst_address_state = form_data.get("gst_address_state")
            gst_address_city = form_data.get("gst_address_city")
            gst_address_building = form_data.get("gst_address_building")
            gst_address_area = form_data.get("gst_address_area")
            gst_address_landmark = form_data.get("gst_address_landmark")
            gst_address_pincode = form_data.get("gst_address_pincode")

            communication_address_country = form_data.get(
                "communication_address_country"
            )
            communication_address_state = form_data.get("communication_address_state")
            communication_address_city = form_data.get("communication_address_city")
            communication_address_building = form_data.get(
                "communication_address_building"
            )
            communication_address_area = form_data.get("communication_address_area")
            communication_address_landmark = form_data.get(
                "communication_address_landmark"
            )
            communication_address_pincode = form_data.get(
                "communication_address_pincode"
            )

            company_logo = request.data.get("company_logo", None)

            if company_name:
                company.name = company_name
            if person_name:
                company.person_name = person_name
            if email:
                company.email = email
            if phone:
                company.phone = phone
            if gst_no:
                company.gst_no = gst_no

            if gst_address_country not in (None, ""):
                company.gst_address_country_id = gst_address_country
            if gst_address_state not in (None, ""):
                company.gst_address_state_id = gst_address_state
            if gst_address_city not in (None, ""):
                company.gst_address_city_id = gst_address_city
            if gst_address_building:
                company.gst_address_building = gst_address_building
            if gst_address_area:
                company.gst_address_area = gst_address_area
            if gst_address_landmark:
                company.gst_address_landmark = gst_address_landmark
            if gst_address_pincode:
                company.gst_address_pincode = gst_address_pincode

            if communication_address_country not in (None, ""):
                company.communication_address_country_id = communication_address_country
            if communication_address_state not in (None, ""):
                company.communication_address_state_id = communication_address_state
            if communication_address_city not in (None, ""):
                company.communication_address_city_id = communication_address_city
            if communication_address_building:
                company.communication_address_building = communication_address_building
            if communication_address_area:
                company.communication_address_area = communication_address_area
            if communication_address_landmark:
                company.communication_address_landmark = communication_address_landmark
            if communication_address_pincode:
                company.communication_address_pincode = communication_address_pincode

            if company_logo and hasattr(company_logo, "read"):
                company.upload_company_logo_presentation(company_logo)

            company.updated_by = request.user
            company.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.update_company_basic_info(company, ip_address, request.user)

            users = User.objects.filter(
                email=company.email, groups__customgroup__company=company
            )
            for user in users:
                if person_name:
                    user.first_name = person_name
                if email:
                    user.email = email
                if phone:
                    user.phone = phone
                user.save()

            return Response(
                {"message": "Company basic info updated successfully."}, status=200
            )

        except Company.DoesNotExist:
            return Response({"error": "Company not found."}, status=404)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON in form_data."}, status=400)

    @action(detail=True, methods=["PATCH"], url_path="change-company-password")
    def change_company_password(self, request, pk=None):
        try:
            company = Company.objects.get(id=pk)
            new_password = request.data.get("new_password")
            re_enter_password = request.data.get("re_enter_password")

            if not (new_password and re_enter_password):
                return Response(
                    {
                        "success": False,
                        "message": "new_password and re_enter_password are required.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_password != re_enter_password:
                return Response(
                    {
                        "success": False,
                        "message": "New password and Re-enter password do not match.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            admin_group = CustomGroup.objects.filter(
                name="Company Admin", company=company
            ).first()
            if admin_group:
                user = (
                    User.objects.filter(groups=admin_group)
                    .order_by("id")
                    .first()
                )
            else:
                user = (
                    User.objects.filter(
                        groups__customgroup__company=company
                    )
                    .order_by("id")
                    .first()
                )

            if not user:
                return Response(
                    {
                        "success": False,
                        "message": "Admin user not found for this company.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.change_company_password(company, ip_address, request.user)

            return Response(
                {"success": True, "message": "Password updated successfully."},
                status=status.HTTP_200_OK,
            )

        except Company.DoesNotExist:
            return Response(
                {"success": False, "message": "Company not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["PATCH"], url_path="update-status")
    def update_company_status(self, request):
        company_id = request.data.get("company_id")
        new_status = request.data.get("status")

        if not company_id:
            return Response(
                {"success": False, "message": "Company ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_status:
            return Response(
                {"success": False, "message": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_statuses = ["active", "inactive", "pending"]
        if new_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "message": (
                        "Invalid status. Must be one of: " + ", ".join(valid_statuses)
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            company = Company.objects.get(id=company_id, deleted=False)
            company.status = new_status
            company.is_active = True if new_status == "active" else False
            company.updated_by = request.user
            company.save()

            is_active_flag = True if new_status == "active" else False
            User.objects.filter(groups__customgroup__company=company).update(
                status=new_status, is_active=is_active_flag
            )

            ip_address = get_client_ip(request)
            ActivityLog.log.update_company_status(company, ip_address, request.user)

            return Response(
                {"success": True, "message": "Company status updated successfully"},
                status=status.HTTP_200_OK,
            )

        except Company.DoesNotExist:
            return Response(
                {"success": False, "message": "Company not found or already deleted"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "message": f"Error updating company status: {str(e)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CompanyArchiveViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Company.objects.filter(deleted=True).order_by("-id")
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "name",
        "company_type",
        "gst_no",
        "email",
        "phone",
        "person_name",
        "status",
        "is_active",
        "business_category__business_category",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "company_logo",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
        "secondary_email",
        "secondary_phone",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
        "instagram_url",
        "youtube_url",
        "pinterest_url",
        "year_of_establishment",
        "number_of_employees",
        "monday_friday_hours",
        "saturday_hours",
        "sunday_hours",
    ]

    ordering_fields = [
        "name",
        "company_type",
        "gst_no",
        "email",
        "phone",
        "person_name",
        "status",
        "is_active",
        "business_category__business_category",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "company_logo",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
        "secondary_email",
        "secondary_phone",
        "facebook_url",
        "twitter_url",
        "linkedin_url",
        "instagram_url",
        "youtube_url",
        "pinterest_url",
        "year_of_establishment",
        "number_of_employees",
        "monday_friday_hours",
        "saturday_hours",
        "sunday_hours",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = CompanyArchiveSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    company = Company.objects.get(id=deleted_id)
                    ActivityLog.log.company_archive(company, ip_address, request.user)
                except Company.DoesNotExist:
                    continue

            serializer.save()

            message = (
                "Company archived successfully"
                if count == 1
                else "Companies archived successfully"
            )
            return Response(
                {"success": True, "message": message},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = CompanyArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = CompanyArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CompanyArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


class CompanyRestoreViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = Company.objects.filter(deleted=True).order_by("id")
    serializer_class = CompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = CompanyRestoreSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    company = Company.objects.get(id=deleted_id)
                    ActivityLog.log.company_restore(company, ip_address, request.user)
                except Company.DoesNotExist:
                    continue

            serializer.save()

            message = (
                "Company restored successfully"
                if count == 1
                else "Companies restored successfully"
            )
            return Response(
                {"success": True, "message": message},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GovtDocumentVerification(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(
        methods=["get"],
        detail=False,
        url_path="gst",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def gst_verification(self, request, *args, **kwargs):
        gst_no = request.query_params.get("gst_no")
        if gst_no:
            data = GovernmentDocVerification().verify_gst(gst_no)
            if "error" in data:
                return Response(
                    {"success": False, "message": "Verification failed"},
                    status=status.HTTP_200_OK,
                )
            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"success": False, "data": "Invalid GST No"}, status=status.HTTP_200_OK
            )

    @action(methods=["get"], detail=False, url_path="udhyam")
    def udhyam_verification(self, request, *args, **kwargs):
        udhyam_no = request.query_params.get("udhyam_no")
        if udhyam_no:
            data = GovernmentDocVerification().verify_udhyam(udhyam_no)
            if "error" in data:
                return Response(
                    {"success": False, "message": "Verification failed"},
                    status=status.HTTP_200_OK,
                )

            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"success": False, "data": "Invalid UDHYAM No"},
                status=status.HTTP_200_OK,
            )

    @action(methods=["get"], detail=False, url_path="pan")
    def pan_verification(self, request, *args, **kwargs):
        pan_no = request.query_params.get("pan_no", None)
        full_name = request.query_params.get("name", None)
        dob = request.query_params.get("dob", None)
        if pan_no:
            data = GovernmentDocVerification().verify_pan(pan_no, full_name, dob)
            if "error" in data:
                return Response(
                    {"success": False, "message": "Verification failed"},
                    status=status.HTTP_200_OK,
                )

            return Response({"success": True, "data": data}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"success": False, "data": "Invalid PAN No"}, status=status.HTTP_200_OK
            )


class CompanyPhotoViewSet(SearchOrderingFilter, ModelViewSet):
    serializer_class = CompanyPhotoSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["title", "photo_file"]
    ordering_fields = ["title", "photo_file"]

    def get_queryset(self):
        company_id = self.request.query_params.get(
            "company_id"
        ) or self.request.data.get("company_id")

        if (
            not company_id
            and hasattr(self.request, "data")
            and "form_data" in self.request.data
        ):
            try:
                form_data = json.loads(self.request.data["form_data"])
                company_id = form_data.get("company_id")
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        if company_id:
            try:

                company = Company.objects.get(id=company_id)
                return CompanyPhoto.objects.filter(
                    deleted=False, company=company
                ).order_by("-id")
            except Company.DoesNotExist:
                return CompanyPhoto.objects.none()
        elif self.request.user.company:
            return CompanyPhoto.objects.filter(
                deleted=False, company=self.request.user.company
            ).order_by("-id")
        else:
            return CompanyPhoto.objects.none()

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
        company_id = request.query_params.get("company_id") or request.data.get(
            "company_id"
        )

        if not company_id and "form_data" in request.data:
            try:
                form_data = json.loads(request.data["form_data"])
                company_id = form_data.get("company_id")
            except (json.JSONDecodeError, KeyError):
                pass

        if company_id:
            try:

                target_company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                return Response(
                    {"success": False, "message": "Company not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif request.user.company:
            target_company = request.user.company
        else:
            return Response(
                {"success": False, "message": "No company context available"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = json.loads(request.data["form_data"])
        data["created_by"] = request.user.id
        data["company"] = target_company.id
        photo_file = request.data.get("photo_file")
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            instance = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.company_photo_create(
                instance, ip_address, request.user, target_company
            )

            company_photo = CompanyPhoto.objects.filter(
                company=target_company, deleted=False
            )
            serializer = CompanyPhotoSerializer(company_photo, many=True)

            if photo_file and hasattr(photo_file, "read"):
                instance.upload_company_photo_presentation(photo_file)
                instance.save()

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = CompanyPhoto.objects.get(id=kwargs["pk"])
            if instance.deleted:
                return Response(
                    {"detail": "No CompanyPhoto matches the given query."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            serializer = self.serializer_class(instance)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except CompanyPhoto.DoesNotExist:
            return Response(
                {"detail": "No CompanyPhoto matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = CompanyPhoto.objects.get(id=kwargs["pk"], deleted=False)
        except CompanyPhoto.DoesNotExist:
            return Response(
                {"detail": "No CompanyPhoto matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = json.loads(request.data["form_data"])
        data["updated_by"] = request.user.id
        photo_file = request.data.get("photo_file", None)
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.company_photo_modify(
                instance, ip_address, request.user, instance.company
            )

            if photo_file and hasattr(photo_file, "read"):
                instance.upload_company_photo_presentation(photo_file)
                instance.save()

            company_id = request.query_params.get("company_id")
            if company_id:
                try:

                    target_company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    target_company = instance.company
            elif request.user.company:
                target_company = request.user.company
            else:
                target_company = instance.company

            company_photo = CompanyPhoto.objects.filter(
                company=target_company, deleted=False
            )
            serializer = CompanyPhotoSerializer(company_photo, many=True)

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
        try:
            instance = CompanyPhoto.objects.get(id=kwargs["pk"])
        except CompanyPhoto.DoesNotExist:
            return Response(
                {"detail": "No CompanyPhoto matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if instance.deleted:
            company_id = request.query_params.get("company_id") or request.data.get(
                "company_id"
            )

            if company_id:
                try:
                    target_company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    target_company = instance.company
            elif request.user.company:
                target_company = request.user.company
            else:
                target_company = instance.company

            company_photo = CompanyPhoto.objects.filter(
                company=target_company, deleted=False
            )
            serializer = CompanyPhotoSerializer(company_photo, many=True)

            return Response(
                {
                    "success": True,
                    "message": "Company Photo Already Deleted",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        company_for_response = instance.company

        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()

        ip_address = get_client_ip(request)
        ActivityLog.log.company_photo_delete(
            instance, ip_address, request.user, instance.company
        )

        company_id = request.query_params.get("company_id") or request.data.get(
            "company_id"
        )

        if company_id:
            try:
                target_company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                target_company = company_for_response
        elif request.user.company:
            target_company = request.user.company
        else:
            target_company = company_for_response

        company_photo = CompanyPhoto.objects.filter(
            company=target_company, deleted=False
        )
        serializer = CompanyPhotoSerializer(company_photo, many=True)

        return Response(
            {
                "success": True,
                "message": "Company Photo Deleted Successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="company-photo-delete")
    def company_photo_delete(self, request, *args, **kwargs):
        try:
            instance = CompanyPhoto.objects.get(id=kwargs["pk"])
        except CompanyPhoto.DoesNotExist:
            return Response(
                {"detail": "No CompanyPhoto matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        photo_file = instance.photo_file

        if photo_file:
            instance.photo_file = None
            instance.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.company_photo_delete(
                instance, ip_address, request.user, instance.company
            )

            return Response(
                {"success": True, "message": "Image deleted"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": "Image not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CompanyPhotoArchiveViewSet(CompanyPhotoArchivedQuerysetMixin, ModelViewSet):
    serializer_class = CompanyPhotoArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["title", "photo_file"]
    ordering_fields = ["title", "photo_file"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = CompanyPhotoSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = CompanyPhotoSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = CompanyPhotoSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = CompanyPhotoArchiveSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    company_photo = CompanyPhoto.objects.get(id=deleted_id)
                    ActivityLog.log.company_photo_delete(
                        company_photo, ip_address, request.user, company_photo.company
                    )
                except CompanyPhoto.DoesNotExist:
                    continue

            serializer.save()
            message = (
                "Company Photo archived successfully"
                if count == 1
                else "Company Photos archived successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CompanyPhotoRestoreViewSet(
    CompanyPhotoArchivedQuerysetMixin,
    MethodNotAllowedListMixin,
    ModelViewSet,
):
    serializer_class = CompanyPhotoRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["title", "photo_file"]
    ordering_fields = ["title", "photo_file"]

    def create(self, request, *args, **kwargs):
        serializer = CompanyPhotoRestoreSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    company_photo = CompanyPhoto.objects.get(id=deleted_id)
                    ActivityLog.log.company_photo_modify(
                        company_photo, ip_address, request.user, company_photo.company
                    )
                except CompanyPhoto.DoesNotExist:
                    continue

            serializer.save()
            message = (
                "Company Photo restored successfully"
                if count == 1
                else "Company Photos restored successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EnquiryViewSet(ModelViewSet):
    queryset = Enquiry.objects.all().order_by("-id")
    serializer_class = EnquirySerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination

    def send_email(self, user, context):
        recipient_email = context.get("company_email")
        if not recipient_email or recipient_email == "N/A":
            recipient_email = config("ADMIN_EMAIL")

        context["email"] = recipient_email

        send_mail(
            "New Enquiry Received - Future4U",
            "enquiry-notification.html",
            context,
        )

    def create(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"success": False, "message": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        is_super_admin = request.user.is_superuser

        is_partner_company = False
        if hasattr(request.user, "partner_company") and request.user.partner_company:
            is_partner_company = True

        if not (is_super_admin or is_partner_company):
            return Response(
                {
                    "success": False,
                    "message": "Access denied. Only super admins and partner companies can create enquiries.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if request.user and request.user.is_authenticated:
                serializer.validated_data["user"] = request.user
            enquiry = serializer.save()

            user_obj = (
                request.user if request.user and request.user.is_authenticated else None
            )

            try:
                context = {
                    "name": enquiry.name,
                    "enquirer_email": enquiry.email,
                    "phone": enquiry.phone,
                    "message": enquiry.message,
                    "user_name": (
                        enquiry.user.get_full_name() if enquiry.user else "Guest User"
                    ),
                    "user_email": enquiry.user.email if enquiry.user else "N/A",
                    "company_name": (
                        enquiry.send_enquiry_to.name
                        if enquiry.send_enquiry_to
                        else "N/A"
                    ),
                    "company_email": (
                        enquiry.send_enquiry_to.email
                        if enquiry.send_enquiry_to
                        else "N/A"
                    ),
                }

                email_thread = threading.Thread(
                    target=self.send_email, args=(user_obj, context)
                )
                email_thread.start()

                return Response(
                    {
                        "success": True,
                        "message": "Enquiry submitted successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Exception:
                return Response(
                    {
                        "success": True,
                        "message": "Enquiry submitted successfully",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        return Response(
            {"success": False, "message": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
