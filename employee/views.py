import json
import threading
from datetime import datetime

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Permission
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

# from bulk_upload.bulk_upload import Employee_BulkUpload
from common.mixins.view_mixins import (
    CreatePasswordEmailMixin,
    RetrieveSuccessEnvelopeMixin,
)
from email_utils.send_email import generate_forget_pass_token, send_mail
from email_utils.send_inactive_email import send_inactive_email
from employee.models import Employee
from employee.serializers import (
    AddEmployeeSerializer,
    EmployeeArchiveListSerializer,
    EmployeeArchiveSerializer,
    EmployeeRestoreSerializer,
    EmployeeStatusSerializer,
)
from user.models import User
from utils.aws_file_upload import delete_uploaded_file
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


# Create your views here.
class EmployeeSearchOrdering:
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "status",
        "user__groups__name",
        "user__user_permissions__name",
        "user__user_permissions__content_type__app_label",
    ]

    ordering_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "status",
        "user__groups__name",
        "user__user_permissions__name",
        "user__user_permissions__content_type__app_label",
        "created_at",
        "updated_at",
    ]


class AddEmployeeViewSet(
    RetrieveSuccessEnvelopeMixin, EmployeeSearchOrdering, ModelViewSet
):
    queryset = Employee.objects.filter(deleted=False).order_by("-id")
    serializer_class = AddEmployeeSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def send_email(self, user, context):
        if user:
            send_mail(
                "Future4U Security Alert For Reset Your Password",
                "reset-pass.html",
                context,
            )

    def get_queryset(self):
        user = self.request.user
        return Employee.objects.filter(
            created_by=user,
            deleted=False,
        ).order_by("-id")

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
        else:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        form_data = request.data.get("form_data")
        if not form_data:
            return Response(
                {"success": False, "message": "form_data is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = json.loads(form_data)
        data["created_by"] = request.user.id
        profile_photo = request.data.get("profile_photo")

        serializer = self.serializer_class(data=data, context={"request": request})

        if serializer.is_valid():
            with transaction.atomic():
                employee = serializer.save()

                if profile_photo:
                    employee.upload_profile_photo_presentation(profile_photo)
                    employee.save()

                serializer = self.serializer_class(employee)
                return Response(
                    {
                        "success": True,
                        "message": "Employee created. Temporary password sent to their email.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            error_messages = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": False, "message": error_messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        form_data = request.data.get("form_data")
        if not form_data:
            return Response(
                {"success": False, "message": "form_data is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = json.loads(form_data)
        data["updated_by"] = request.user.id
        profile_photo = request.data.get("profile_photo")
        serializer = self.serializer_class(
            instance, data=data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            instance = serializer.save()

            if profile_photo:
                instance.upload_profile_photo_presentation(profile_photo)

            instance.save()

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            errors_message = " ".join(
                [", ".join(value) for value in serializer.errors.values()]
            )
            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.updated_by = request.user
        instance.updated_at = now()
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()
        return Response(
            {"success": True, "message": "Employee Deleted"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="profile-photo-delete")
    def profile_photo_delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.profile_photo:
            delete_uploaded_file(instance.profile_photo)
            instance.profile_photo = None
            instance.updated_by = request.user
            instance.updated_at = now()
            instance.save()
            return Response(
                {"success": True, "message": "Profile Photo Deleted Successfully"},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": "Profile Photo Not Found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["get"], url_path="get-company-employees")
    def get_company_employees(self, request, *args, **kwargs):
        user = self.request.user

        employee_list = None
        if user.company:
            company_instance = user.company
            employee_list = Employee.objects.filter(
                created_by__company=company_instance, deleted=False
            ).order_by("-id")

        else:
            super_user_instance = user
            employee_list = Employee.objects.filter(
                created_by=super_user_instance, deleted=False
            ).order_by("-id")

        result_page = None
        if employee_list is not None:
            employee = self.filter_queryset(employee_list)
            pagination = Pagination()
            result_page = pagination.paginate_queryset(employee, request)

            serializer = AddEmployeeSerializer(
                result_page, many=True, context={"request": request}
            )
            return pagination.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        else:
            serializer = AddEmployeeSerializer(
                result_page, many=True, context={"request": request}
            )
            return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"], url_path="employees-by-company")
    def employees_by_company(self, request, *args, **kwargs):
        user = self.request.user

        if user.company:
            company_instance = user.company
            users = User.objects.filter(
                employee__in=Employee.objects.filter(
                    created_by__company=company_instance, status="active", deleted=False
                )
            )

        else:
            super_user_instance = user
            users = User.objects.filter(
                employee__in=Employee.objects.filter(
                    created_by=super_user_instance, status="active", deleted=False
                )
            )

        pagination = Pagination()
        result_page = pagination.paginate_queryset(users, request)

        employee_data = [
            {
                "id": user.id,
                "employee_id": user.employee.id,
                "first_name": user.employee.first_name,
                "last_name": user.employee.last_name,
                "phone": user.employee.phone,
            }
            for user in result_page
        ]

        return pagination.get_paginated_response(
            {"success": True, "data": employee_data}
        )

    @action(detail=False, methods=["get"], url_path="employees-by-partner-company")
    def employees_by_partner_company(self, request, *args, **kwargs):
        partner_company_id = request.query_params.get("partner_company_id")

        if not partner_company_id:
            return Response(
                {
                    "success": False,
                    "message": "partner_company_id query parameter is required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            partner_company_id = int(partner_company_id)
        except ValueError:
            return Response(
                {
                    "success": False,
                    "message": "partner_company_id must be a valid integer",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # try:
        #     technician_group = CustomGroup.objects.get(
        #         group_name="Technician",
        #         partner_company_id=partner_company_id
        #     )
        #     technician_role_id = str(technician_group.id)
        # except CustomGroup.DoesNotExist:
        #     return Response(
        #         {"success": True, "data": [], "message": "No technician role found for this partner company"},
        #         status=status.HTTP_200_OK,
        #     )

        employee_list = Employee.objects.filter(
            user__partner_company_id=partner_company_id,
            # user__role=technician_role_id,
            status="active",
            deleted=False,
        ).order_by("-id")

        if not employee_list.exists():
            return Response(
                {
                    "success": True,
                    "data": [],
                    "message": "No employees found for this partner company",
                },
                status=status.HTTP_200_OK,
            )

        # Apply filtering and pagination
        employee_list = self.filter_queryset(employee_list)
        pagination = Pagination()
        result_page = pagination.paginate_queryset(employee_list, request)

        serializer = AddEmployeeSerializer(
            result_page, many=True, context={"request": request}
        )
        return pagination.get_paginated_response(
            {"success": True, "data": serializer.data}
        )

    @action(detail=False, methods=["get"], url_path="employees-list")
    def employees_list(self, request, *args, **kwargs):
        user = self.request.user

        queryset = Employee.objects.filter(
            created_by=user, status="active", deleted=False
        ).order_by("-id")

        queryset = self.filter_queryset(queryset)

        def to_minimal(emp):
            full_name = f"{emp.first_name} {emp.middle_name} {emp.last_name}".strip()
            return {"id": emp.id, "employee_name": full_name}

        data = [to_minimal(e) for e in queryset]
        return Response({"success": True, "data": data})

    @action(detail=False, methods=["get"], url_path="get-po-release-manager")
    def get_po_release_manager(self, request, *args, **kwargs):
        user = self.request.user

        allotted_permission = [
            "add_poorder",
            "change_poorder",
            "delete_poorder",
            "view_poorder",
        ]
        permission = Permission.objects.filter(codename__in=allotted_permission)

        if user.company:
            company_instance = user.company
            users = User.objects.filter(
                user_permissions__in=permission,
                employee__in=Employee.objects.filter(
                    created_by__company=company_instance, status="active", deleted=False
                ),
            ).distinct()

        else:
            return Response(
                {"success": False, "message": "User does not belong to any company."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pagination = Pagination()
        result_page = pagination.paginate_queryset(users, request)

        employee_data = [
            {
                "id": user.employee.id,
                "first_name": user.employee.first_name,
                "phone": user.employee.phone,
            }
            for user in result_page
        ]

        return pagination.get_paginated_response(
            {"success": True, "data": employee_data}
        )

    @action(detail=True, methods=["GET"], url_path="employee-basic-info")
    def get_employee_basic_info(self, request, pk=None):
        try:
            employee = Employee.objects.get(id=pk, deleted=False)

            data = {
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "email": employee.email,
                "phone": employee.phone,
            }
            return Response(data, status=200)

        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)

    @action(detail=True, methods=["PATCH"], url_path="update-employee-details")
    def update_employee_details(self, request, pk=None):
        try:
            employee = Employee.objects.get(id=pk, deleted=False)

            form_data = request.data.get("form_data")

            if not form_data:
                return Response(
                    {"error": "form_data is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                data = json.loads(form_data)
            except json.JSONDecodeError:
                return Response(
                    {"error": "Invalid JSON format in form_data."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            first_name = data.get("first_name")
            last_name = data.get("last_name")
            phone = data.get("phone")

            if first_name:
                employee.first_name = first_name
            if last_name:
                employee.last_name = last_name
            if phone:
                employee.phone = phone

            employee.updated_by = request.user
            employee.updated_at = now()
            employee.save()

            users = User.objects.filter(employee=employee)
            for user in users:
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                if phone:
                    user.phone = phone
                user.save()

            return Response(
                {"message": "Employee details updated successfully."},
                status=status.HTTP_200_OK,
            )

        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["PATCH"], url_path="change-employee-password")
    def change_employee_password(self, request, pk=None):
        try:
            employee = Employee.objects.get(id=pk)
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

            user = User.objects.filter(employee=employee).first()

            if not user:
                return Response(
                    {"error": "Admin user not found for this employee."}, status=404
                )

            if not check_password(old_password, user.password):
                return Response({"error": "Old password is incorrect."}, status=400)

            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()

            employee.updated_by = request.user
            employee.updated_at = now()
            employee.save()

            return Response({"message": "Password updated successfully."}, status=200)

        except Employee.DoesNotExist:
            return Response({"error": "Employee not found."}, status=404)


# Employee Status
class EmployeeStatusViewSet(
    CreatePasswordEmailMixin, EmployeeSearchOrdering, ModelViewSet
):
    queryset = Employee.objects.filter(deleted=False).order_by("-id")
    serializer_class = EmployeeStatusSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data
        serializer = self.serializer_class(
            instance, data=data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            with transaction.atomic():
                user = User.objects.get(employee=instance)
                instance.updated_by = request.user
                instance.updated_at = datetime.now()
                instance = serializer.save()

                email = instance.email
                user_phone = instance.phone
                if instance.status == "active":
                    user.status = "active"
                    user.is_active = True
                    user.save()

                    token = generate_forget_pass_token(email, user_phone, 30)
                    name = instance.first_name + " " + instance.last_name

                    phonenumber = str(user_phone)
                    if phonenumber.startswith("91"):
                        phonenumber = phonenumber[2:]
                    # whatsapp_messages = WhatsappMessages("reset_password", phonenumber)

                    # company_instance = Company.objects.filter(email=email).first()
                    # employee_instance = Employee.objects.filter(email=email).first()

                    # whatsapp_messages.send_reset_password(
                    #     phonenumber,
                    #     name,
                    #     password_link,
                    #     company_instance,
                    #     employee_instance,
                    # )

                    context = {"name": name, "token": token, "email": email}
                    email_thread = threading.Thread(
                        target=self.send_email,
                        args=(instance, context),
                    )
                    email_thread.start()

                    return Response(
                        {
                            "success": True,
                            "message": "Reset Password Mail has been sent to registered email",
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    instance.status = "inactive"
                    # Create a mutable copy of the data
                    data = data.copy()
                    data["name"] = instance.first_name
                    data["email"] = instance.email
                    data["status"] = instance.status
                    instance.save()
                    user.status = "inactive"
                    user.is_active = False
                    user.save()

                    # whatsapp_messages = WhatsappMessages("employee_deactivated", to)
                    # whatsapp_messages.send_employee_deactivated(
                    #     to,
                    #     employee_id,
                    #     first_name,
                    #     last_name,
                    #     email,
                    #     designation,
                    #     deactivator,
                    #     deactivated_at,
                    #     request_user,
                    # )
                    send_inactive_email(
                        "Important Notice: Your Future4U Account Has Been Deactivated",
                        "user-inactive-email.html",
                        data,
                    )
                    return Response(
                        {"success": True, "message": "Account has been Deactivated"},
                        status=status.HTTP_200_OK,
                    )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class EmployeeArchiveViewSet(ModelViewSet):
    queryset = Employee.objects.filter(deleted=True).order_by("-id")
    serializer_class = EmployeeArchiveSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "status",
        "user__groups__name",
        "user__user_permissions__name",
        "user__user_permissions__content_type__app_label",
    ]

    ordering_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "status",
        "user__groups__name",
        "user__user_permissions__name",
        "user__user_permissions__content_type__app_label",
        "created_at",
        "updated_at",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = EmployeeArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EmployeeArchiveListSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )
        serializer = EmployeeArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = EmployeeArchiveSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            serializer.save()

            message = (
                "User archived successfully"
                if count == 1
                else "Users archived successfully"
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

    @action(detail=False, methods=["get"], url_path="get-archive-company-employees")
    def get_archive_company_employees(self, request, *args, **kwargs):
        user = self.request.user

        employee_list = None
        if user.company:
            company_instance = user.company
            employee_list = Employee.objects.filter(
                created_by__company=company_instance, deleted=True
            ).order_by("-id")

        else:
            super_user_instance = user
            employee_list = Employee.objects.filter(
                created_by=super_user_instance, deleted=True
            ).order_by("-id")

        employee = self.filter_queryset(employee_list)
        pagination = Pagination()
        result_page = pagination.paginate_queryset(employee, request)

        serializer = AddEmployeeSerializer(result_page, many=True)
        return pagination.get_paginated_response(
            {"success": True, "data": serializer.data}
        )


class EmployeeRestoreViewSet(ModelViewSet):
    queryset = Employee.objects.filter(deleted=True).order_by("-id")
    serializer_class = EmployeeRestoreSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = EmployeeRestoreSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            deleted_ids = serializer.validated_data.get("deleted", [])
            if not isinstance(deleted_ids, list):
                deleted_ids = [deleted_ids]
            flat_ids = []
            for x in deleted_ids:
                if isinstance(x, list):
                    flat_ids.extend(x)
                else:
                    flat_ids.append(x)
            try:
                flat_ids = [int(x) for x in flat_ids]
            except (TypeError, ValueError):
                return Response(
                    {
                        "success": False,
                        "message": "'deleted' must be a list of integer IDs",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()

            # Log restore per employee with correct signature
            for emp_id in flat_ids:
                try:
                    employee = Employee.objects.get(id=emp_id)
                except Employee.DoesNotExist:
                    continue
                user = User.objects.filter(employee=employee).first()
                # Log employee restore activity
                ip_address = get_client_ip(request)
                company = getattr(user, "company", None) if user else None
                partner_company = (
                    getattr(user, "partner_company", None) if user else None
                )
                ActivityLog.log.employee_restore(
                    employee, ip_address, user, company, partner_company
                )

            count = len(flat_ids)
            message = (
                "User restored successfully"
                if count == 1
                else "Users restored successfully"
            )
            return Response(
                {"success": True, "message": message}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BulkEmployeeViewSet(EmployeeSearchOrdering, ModelViewSet):
    queryset = Employee.objects.filter(deleted=False).order_by("-id")
    serializer_class = AddEmployeeSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    # def create(self, request, *args, **kwargs):
    #     upload_file = request.data.get("upload_file")
    #     if upload_file:
    #         bulk_upload = Employee_BulkUpload(upload_file=upload_file, context={"request": request})
    #         value = bulk_upload.process_employee_csv()
    #         return Response(value)
    #     else:
    #         return Response(
    #             {"success": False, "message": "File not found"},
    #             status=status.HTTP_400_BAD_REQUEST,
    #         )
