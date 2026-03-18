import json
import threading

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.timezone import now
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from email_utils.send_email import generate_forget_pass_token, send_mail
from partner_company.models import PartnerCompany, PartnerCompanyDocument
from partner_company.serializers import (
    PartnerCompanyArchiveListSerializer,
    PartnerCompanyArchiveSerializer,
    PartnerCompanyDocumentArchiveSerializer,
    PartnerCompanyDocumentRestoreSerializer,
    PartnerCompanyDocumentSerializer,
    PartnerCompanyInfoSerializer,
    PartnerCompanyRestoreSerializer,
    PartnerCompanySerializer,
)
from user.models import CustomGroup, User
from utils.aws_file_upload import delete_uploaded_file
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class SearchOrderingFilter:
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "company_name",
        "gst_no",
        "person_name",
        "email",
        "phone",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
    ]

    ordering_fields = [
        "company_name",
        "gst_no",
        "person_name",
        "email",
        "phone",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "status",
        "is_active",
        "created_at",
        "updated_at",
    ]


class PartnerCompanyViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = PartnerCompany.objects.filter(deleted=False).order_by("-id")
    serializer_class = PartnerCompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def send_email(self, user, context):
        if user:
            send_mail(
                "OutdoorX Security Alert For Create New Password",
                "reset-pass.html",
                context,
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PartnerCompanyInfoSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = PartnerCompanyInfoSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        data["created_by"] = request.user.id

        partner_company_logo = request.data.get("partner_company_logo")

        serializer = PartnerCompanySerializer(data=data, context={"request": request})

        if serializer.is_valid():
            with transaction.atomic():
                instance = serializer.save()

                ip_address = get_client_ip(request)
                ActivityLog.log.partner_company_create(instance, ip_address, request.user)

                serializer = PartnerCompanyInfoSerializer(instance)
                email = data["email"]
                user_phone = data["phone"]
                name = data["person_name"]

                if partner_company_logo and hasattr(partner_company_logo, "read"):
                    instance.upload_partner_company_logo_presentation(partner_company_logo)
                    instance.save()

                token = generate_forget_pass_token(email, user_phone, 30)

                phonenumber = str(user_phone)
                if phonenumber.startswith("91"):
                    phonenumber = phonenumber[2:]

                context = {"name": name, "token": token, "email": email}
                email_thread = threading.Thread(target=self.send_email, args=(instance, context))
                email_thread.start()
                return Response(
                    {
                        "success": True,
                        "message": "Reset Password Mail has been sent " "to registered email",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            errors_message = " ".join([", ".join(value) for value in serializer.errors.values()])  # type: ignore
            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = json.loads(request.data["form_data"])
        data["updated_by"] = request.user.id
        partner_company_logo = request.data.get("partner_company_logo")

        serializer = PartnerCompanySerializer(instance, data=data, context={"request": request}, partial=True)

        if serializer.is_valid():
            instance.updated_by = request.user
            partner_company = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.partner_company_update(partner_company, ip_address, request.user)

            # Only upload new logo if partner_company_logo is provided and is not a string (URL)
            if partner_company_logo and hasattr(partner_company_logo, "read"):
                instance.upload_partner_company_logo_presentation(partner_company_logo)
                instance.save()

            serializer = PartnerCompanyInfoSerializer(partner_company)
            return Response(
                {"success": True, "message": "Partner Company updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            errors_message = " ".join([", ".join(value) for value in serializer.errors.values()])
            return Response(
                {"success": False, "errors": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PartnerCompanyInfoSerializer(instance)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()

        ip_address = get_client_ip(request)
        ActivityLog.log.partner_company_archive(instance, ip_address, request.user)

        return Response({"success": True, "message": "Partner Company Delete"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="partner-company-logo-delete")
    def partner_company_logo_delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.partner_company_logo:
            delete_uploaded_file(instance.partner_company_logo)
            instance.partner_company_logo = None
            instance.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.company_logo_delete(instance, ip_address, request.user)

            return Response(
                {"success": True, "message": "Partner Company Logo Deleted Successfully."},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": "Partner Company Logo Not Found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_path="partner-company-basic-info")
    def get_partner_company_basic_info(self, request, pk=None):
        try:
            partner_company = PartnerCompany.objects.get(id=pk, deleted=False)

            data = {
                "partner_company_logo": partner_company.partner_company_logo,
                "partner_company_name": partner_company.company_name,
                "person_name": partner_company.person_name,
                "email": partner_company.email,
                "phone": partner_company.phone,
                "gst_no": partner_company.gst_no,
                "gst_address_country": partner_company.gst_address_country,
                "gst_address_state": partner_company.gst_address_state,
                "gst_address_city": partner_company.gst_address_city,
                "gst_address_building": partner_company.gst_address_building,
                "gst_address_area": partner_company.gst_address_area,
                "gst_address_landmark": partner_company.gst_address_landmark,
                "gst_address_pincode": partner_company.gst_address_pincode,
                "communication_address_country": partner_company.communication_address_country,
                "communication_address_state": partner_company.communication_address_state,
                "communication_address_city": partner_company.communication_address_city,
                "communication_address_building": partner_company.communication_address_building,
                "communication_address_area": partner_company.communication_address_area,
                "communication_address_landmark": partner_company.communication_address_landmark,
                "communication_address_pincode": partner_company.communication_address_pincode,
            }
            return Response(data, status=200)

        except PartnerCompany.DoesNotExist:
            return Response({"error": "Partner Company not found."}, status=404)

    @action(detail=True, methods=["PATCH"], url_path="update-paryner-company-basic-info")
    def update_partner_company_basic_info(self, request, pk=None):
        try:
            partner_company = PartnerCompany.objects.get(id=pk)
            form_data = json.loads(request.data.get("form_data", "{}"))

            # Extract all fields from form_data
            company_name = form_data.get("company_name")
            person_name = form_data.get("person_name")
            email = form_data.get("email")
            phone = form_data.get("phone")
            gst_no = form_data.get("gst_no")

            # GST Address fields
            gst_address_country = form_data.get("gst_address_country")
            gst_address_state = form_data.get("gst_address_state")
            gst_address_city = form_data.get("gst_address_city")
            gst_address_building = form_data.get("gst_address_building")
            gst_address_area = form_data.get("gst_address_area")
            gst_address_landmark = form_data.get("gst_address_landmark")
            gst_address_pincode = form_data.get("gst_address_pincode")

            # Communication Address fields
            communication_address_country = form_data.get("communication_address_country")
            communication_address_state = form_data.get("communication_address_state")
            communication_address_city = form_data.get("communication_address_city")
            communication_address_building = form_data.get("communication_address_building")
            communication_address_area = form_data.get("communication_address_area")
            communication_address_landmark = form_data.get("communication_address_landmark")
            communication_address_pincode = form_data.get("communication_address_pincode")

            partner_company_logo = request.data.get("partner_company_logo", None)

            # Update Company Model
            if company_name:
                partner_company.company_name = company_name
            if person_name:
                partner_company.person_name = person_name
            if email:
                partner_company.email = email
            if phone:
                partner_company.phone = phone
            if gst_no:
                partner_company.gst_no = gst_no

            # Update GST Address
            if gst_address_country:
                partner_company.gst_address_country = gst_address_country
            if gst_address_state:
                partner_company.gst_address_state = gst_address_state
            if gst_address_city:
                partner_company.gst_address_city = gst_address_city
            if gst_address_building:
                partner_company.gst_address_building = gst_address_building
            if gst_address_area:
                partner_company.gst_address_area = gst_address_area
            if gst_address_landmark:
                partner_company.gst_address_landmark = gst_address_landmark
            if gst_address_pincode:
                partner_company.gst_address_pincode = gst_address_pincode

            # Update Communication Address
            if communication_address_country:
                partner_company.communication_address_country = communication_address_country
            if communication_address_state:
                partner_company.communication_address_state = communication_address_state
            if communication_address_city:
                partner_company.communication_address_city = communication_address_city
            if communication_address_building:
                partner_company.communication_address_building = communication_address_building
            if communication_address_area:
                partner_company.communication_address_area = communication_address_area
            if communication_address_landmark:
                partner_company.communication_address_landmark = communication_address_landmark
            if communication_address_pincode:
                partner_company.communication_address_pincode = communication_address_pincode

            if partner_company_logo and hasattr(partner_company_logo, "read"):
                partner_company.upload_partner_company_logo_presentation(partner_company_logo)

            partner_company.updated_by = request.user
            partner_company.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.update_company_basic_info(partner_company, ip_address, request.user)

            # Update associated users
            users = User.objects.filter(company=partner_company)
            for user in users:
                if person_name:
                    user.first_name = person_name
                if email:
                    user.email = email
                if phone:
                    user.phone = phone
                user.save()

            return Response({"message": "Partner Company basic info updated successfully."}, status=200)

        except PartnerCompany.DoesNotExist:
            return Response({"error": "Partner Company not found."}, status=404)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON in form_data."}, status=400)

    @action(detail=True, methods=["PATCH"], url_path="change-partner-company-password")
    def change_partner_company_password(self, request, pk=None):
        try:
            partner_company = PartnerCompany.objects.get(id=pk)
            new_password = request.data.get("new_password")
            re_enter_password = request.data.get("re_enter_password")

            if not (new_password and re_enter_password):
                return Response(
                    {"success": False, "message": "new_password and re_enter_password are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if new_password != re_enter_password:
                return Response(
                    {"success": False, "message": "New password and Re-enter password do not match."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            admin_group = CustomGroup.objects.filter(
                name="Partner Company Admin", partner_company=partner_company
            ).first()
            if admin_group:
                user = User.objects.filter(partner_company=partner_company, groups=admin_group).order_by("id").first()
            else:
                user = User.objects.filter(partner_company=partner_company, role__isnull=False).order_by("id").first()

            if not user:
                return Response(
                    {"success": False, "message": "Admin user not found for this partner company."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.change_partner_company_password(partner_company, ip_address, request.user)

            return Response({"success": True, "message": "Password updated successfully."}, status=status.HTTP_200_OK)

        except PartnerCompany.DoesNotExist:
            return Response(
                {"success": False, "message": "Partner Company not found."}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["PATCH"], url_path="update-partner-company-status")
    def update_partner_company_status(self, request):
        partner_company_id = request.data.get("partner_company_id")
        new_status = request.data.get("status")

        if not partner_company_id:
            return Response(
                {"success": False, "message": "Partner Company ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not new_status:
            return Response({"success": False, "message": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate status
        valid_statuses = ["active", "inactive", "pending"]
        if new_status not in valid_statuses:
            return Response(
                {"success": False, "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            partner_company = PartnerCompany.objects.get(id=partner_company_id, deleted=False)
            partner_company.status = new_status
            partner_company.is_active = True if new_status == "active" else False
            partner_company.updated_by = request.user
            partner_company.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.update_partner_company_status(partner_company, ip_address, request.user)

            is_active_flag = True if new_status == "active" else False
            User.objects.filter(partner_company=partner_company).update(status=new_status, is_active=is_active_flag)

            return Response(
                {"success": True, "message": "Partner Company status updated successfully"}, status=status.HTTP_200_OK
            )

        except PartnerCompany.DoesNotExist:
            return Response(
                {"success": False, "message": "Partner Company not found or already deleted"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error updating partner company status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Partner Company Multiple Archive
class PartnerCompanyArchiveViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = PartnerCompany.objects.filter(deleted=True).order_by("-id")
    serializer_class = PartnerCompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "company_name",
        "gst_no",
        "person_name",
        "email",
        "phone",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "gst_address_building",
        "gst_address_area__city_area_name",
        "gst_address_landmark",
        "gst_address_pincode",
        "communication_address_building",
        "communication_address_area__city_area_name",
        "communication_address_landmark",
        "communication_address_pincode",
    ]

    ordering_fields = [
        "company_name",
        "gst_no",
        "person_name",
        "email",
        "phone",
        "gst_address_country__name",
        "gst_address_state__name",
        "gst_address_city__name",
        "communication_address_country__name",
        "communication_address_state__name",
        "communication_address_city__name",
        "status",
        "is_active",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = PartnerCompanyArchiveSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            # Determine count for pluralized message
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            # Add activity logging for each archived partner company
            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    partner_company_instance = PartnerCompany.objects.get(id=deleted_id)
                    ActivityLog.log.partner_company_archive(partner_company_instance, ip_address, request.user)
                except PartnerCompany.DoesNotExist:
                    continue

            serializer.save()

            message = (
                "Partner Company archived successfully" if count == 1 else "Partner Companies archived successfully"
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
            serializer = PartnerCompanyArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PartnerCompanyArchiveListSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = PartnerCompanyArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


# Partner Company Multiple Restore
class PartnerCompanyRestoreViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = PartnerCompany.objects.filter(deleted=True).order_by("id")
    serializer_class = PartnerCompanyInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = PartnerCompanyRestoreSerializer(data=request.data)
        if serializer.is_valid():
            # Determine count for pluralized message
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            # Add activity logging for each restored partner company
            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    partner_company_instance = PartnerCompany.objects.get(id=deleted_id)
                    ActivityLog.log.partner_company_restore(partner_company_instance, ip_address, request.user)
                except PartnerCompany.DoesNotExist:
                    continue

            serializer.save()

            message = (
                "Partner Company restored successfully" if count == 1 else "Partner Companies restored successfully"
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


class PartnerCompanyDocumentViewSet(SearchOrderingFilter, ModelViewSet):
    serializer_class = PartnerCompanyDocumentSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["document_title", "document_file"]
    ordering_fields = ["document_title", "document_file"]

    def get_queryset(self):
        # Check if partner_company_id is provided (query param, POST data, or form data)
        partner_company_id = self.request.query_params.get("partner_company_id") or self.request.data.get(
            "partner_company_id"
        )

        # Also check in form_data JSON if available
        if not partner_company_id and hasattr(self.request, "data") and "form_data" in self.request.data:
            try:
                form_data = json.loads(self.request.data["form_data"])
                partner_company_id = form_data.get("partner_company_id")
            except (json.JSONDecodeError, KeyError, AttributeError):
                pass

        if partner_company_id:
            # Admin is editing a specific partner company, show only that company's documents
            try:
                from partner_company.models import PartnerCompany

                partner_company = PartnerCompany.objects.get(id=partner_company_id)
                return PartnerCompanyDocument.objects.filter(deleted=False, partner_company=partner_company).order_by(
                    "-id"
                )
            except PartnerCompany.DoesNotExist:
                return PartnerCompanyDocument.objects.none()
        elif self.request.user.partner_company:
            # Regular partner company user, show only their own documents
            return PartnerCompanyDocument.objects.filter(
                deleted=False, partner_company=self.request.user.partner_company
            ).order_by("-id")
        else:
            # If no partner company context, return empty queryset
            return PartnerCompanyDocument.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True, context={"request": request})
            return Response({"success": True, "data": serializer.data})

        if page:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data},
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        # Check if partner_company_id is provided (query param or form data or directly as parameter)
        partner_company_id = request.query_params.get("partner_company_id") or request.data.get("partner_company_id")

        # If not in query params or direct data, check in form_data JSON
        if not partner_company_id and "form_data" in request.data:
            try:
                form_data = json.loads(request.data["form_data"])
                partner_company_id = form_data.get("partner_company_id")
            except (json.JSONDecodeError, KeyError):
                pass

        if partner_company_id:
            # Admin is creating document for a specific partner company
            try:
                from partner_company.models import PartnerCompany

                target_partner_company = PartnerCompany.objects.get(id=partner_company_id)
            except PartnerCompany.DoesNotExist:
                return Response(
                    {"success": False, "message": "Partner company not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif request.user.partner_company:
            # Regular partner company user creating their own document
            target_partner_company = request.user.partner_company
        else:
            return Response(
                {"success": False, "message": "No partner company context available"},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = json.loads(request.data["form_data"])
        data["created_by"] = request.user.id
        # Set the partner company - use the target one we determined above
        data["partner_company"] = target_partner_company.id
        document_file = request.data.get("document_file")
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            instance = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.partner_company_document_create(instance, ip_address, request.user, target_partner_company)

            # Filter to get only target partner company documents
            partner_company_document = PartnerCompanyDocument.objects.filter(
                partner_company=target_partner_company, deleted=False
            )
            serializer = PartnerCompanyDocumentSerializer(partner_company_document, many=True)

            if document_file and hasattr(document_file, "read"):
                instance.upload_partner_company_document_presentation(document_file)
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
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        data = json.loads(request.data["form_data"])
        data["updated_by"] = request.user.id
        document_file = request.data.get("document_file", None)
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.partner_company_document_modify(
                instance, ip_address, request.user, instance.partner_company
            )

            if document_file and hasattr(document_file, "read"):
                instance.upload_partner_company_document_presentation(document_file)
                instance.save()

            # Determine which partner company's documents to return
            partner_company_id = request.query_params.get("partner_company_id")
            if partner_company_id:
                try:
                    from partner_company.models import PartnerCompany

                    target_partner_company = PartnerCompany.objects.get(id=partner_company_id)
                except PartnerCompany.DoesNotExist:
                    target_partner_company = instance.partner_company
            elif request.user.partner_company:
                target_partner_company = request.user.partner_company
            else:
                target_partner_company = instance.partner_company

            # Filter to get only target partner company documents
            partner_company_document = PartnerCompanyDocument.objects.filter(
                partner_company=target_partner_company, deleted=False
            )
            serializer = PartnerCompanyDocumentSerializer(partner_company_document, many=True)

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

        # Store partner company for response context
        partner_company_for_response = instance.partner_company

        # Mark as deleted (soft delete)
        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()

        ip_address = get_client_ip(request)
        ActivityLog.log.partner_company_document_archive(instance, ip_address, request.user, instance.partner_company)

        # Determine which partner company's documents to return after deletion
        partner_company_id = request.query_params.get("partner_company_id") or request.data.get("partner_company_id")

        if partner_company_id:
            try:
                from partner_company.models import PartnerCompany

                target_partner_company = PartnerCompany.objects.get(id=partner_company_id)
            except PartnerCompany.DoesNotExist:
                target_partner_company = partner_company_for_response
        elif request.user.partner_company:
            target_partner_company = request.user.partner_company
        else:
            target_partner_company = partner_company_for_response

        # Return updated list of documents for the target partner company
        partner_company_documents = PartnerCompanyDocument.objects.filter(
            partner_company=target_partner_company, deleted=False
        )
        serializer = PartnerCompanyDocumentSerializer(partner_company_documents, many=True)

        return Response(
            {"success": True, "message": "Partner Company Document Deleted Successfully", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    # Partner Company Image Delete
    @action(detail=True, methods=["delete"], url_path="partner-company-document-delete")
    def partner_company_document_delete(self, request, *args, **kwargs):
        instance = self.get_object()
        document_file = instance.document_file

        if document_file:
            instance.document_file = None
            instance.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.partner_company_document_archive(
                instance, ip_address, request.user, instance.partner_company
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


# Partner Company Document Archive ViewSet
class PartnerCompanyDocumentArchiveViewSet(ModelViewSet):
    serializer_class = PartnerCompanyDocumentArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["document_title", "document_file"]
    ordering_fields = ["document_title", "document_file"]

    def get_queryset(self):
        # Check if partner_company_id is provided as query parameter
        partner_company_id = self.request.query_params.get("partner_company_id")

        if partner_company_id:
            # Admin is viewing documents for a specific partner company
            try:
                from partner_company.models import PartnerCompany

                partner_company = PartnerCompany.objects.get(id=partner_company_id)
                return PartnerCompanyDocument.objects.filter(deleted=True, partner_company=partner_company).order_by(
                    "-id"
                )
            except PartnerCompany.DoesNotExist:
                return PartnerCompanyDocument.objects.none()
        elif self.request.user.partner_company:
            # Regular partner company user, show only their own documents for archiving
            return PartnerCompanyDocument.objects.filter(
                deleted=True, partner_company=self.request.user.partner_company
            ).order_by("-id")
        else:
            # If no partner company context, return empty queryset
            return PartnerCompanyDocument.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = PartnerCompanyDocumentSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = PartnerCompanyDocumentSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = PartnerCompanyDocumentSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = PartnerCompanyDocumentArchiveSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            # Add activity logging for each archived document
            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    partner_company_document = PartnerCompanyDocument.objects.get(id=deleted_id)
                    ActivityLog.log.partner_company_document_archive(
                        partner_company_document, ip_address, request.user, partner_company_document.partner_company
                    )
                except PartnerCompanyDocument.DoesNotExist:
                    continue

            serializer.save()
            message = (
                "Partner Company Document archived successfully"
                if count == 1
                else "Partner Company Documents archived successfully"
            )
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Partner Company Document Restore ViewSet
class PartnerCompanyDocumentRestoreViewSet(ModelViewSet):
    serializer_class = PartnerCompanyDocumentRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = ["document_title", "document_file"]
    ordering_fields = ["document_title", "document_file"]

    def get_queryset(self):
        # Check if partner_company_id is provided as query parameter
        partner_company_id = self.request.query_params.get("partner_company_id")

        if partner_company_id:
            # Admin is viewing archived documents for a specific partner company
            try:
                from partner_company.models import PartnerCompany

                partner_company = PartnerCompany.objects.get(id=partner_company_id)
                return PartnerCompanyDocument.objects.filter(deleted=True, partner_company=partner_company).order_by(
                    "-id"
                )
            except PartnerCompany.DoesNotExist:
                return PartnerCompanyDocument.objects.none()
        elif self.request.user.partner_company:
            # Regular partner company user, show only their own archived documents for restoring
            return PartnerCompanyDocument.objects.filter(
                deleted=True, partner_company=self.request.user.partner_company
            ).order_by("-id")
        else:
            # If no partner company context, return empty queryset
            return PartnerCompanyDocument.objects.none()

    def list(self, request, *args, **kwargs):
        return Response({"success": False, "message": "Method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request, *args, **kwargs):
        serializer = PartnerCompanyDocumentRestoreSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1

            # Add activity logging for each restored document
            ip_address = get_client_ip(request)
            for deleted_id in deleted_ids:
                try:
                    partner_company_document = PartnerCompanyDocument.objects.get(id=deleted_id)
                    ActivityLog.log.partner_company_document_restore(
                        partner_company_document, ip_address, request.user, partner_company_document.partner_company
                    )
                except PartnerCompanyDocument.DoesNotExist:
                    continue

            serializer.save()
            message = (
                "Partner Company Document restored successfully"
                if count == 1
                else "Partner Company Documents restored successfully"
            )
            return Response({"success": True, "message": message}, status=status.HTTP_200_OK)

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
