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
from end_client.models import EndClient
from end_client.serializers import (
    EndClientArchiveListSerializer,
    EndClientArchiveSerializer,
    EndClientInfoSerializer,
    EndClientRestoreSerializer,
    EndClientSerializer,
)
from user.models import CustomGroup, User
from utils.aws_file_upload import delete_uploaded_file
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination


class SearchOrderingFilter:
    filter_backends = [SearchFilter, OrderingFilter]

    search_fields = [
        "name",
        "email",
        "phone",
        "status",
    ]

    ordering_fields = [
        "name",
        "email",
        "phone",
        "status",
        "created_at",
        "updated_at",
    ]


class EndClientViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = EndClient.objects.filter(deleted=False).order_by("-id")
    serializer_class = EndClientInfoSerializer
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
            serializer = EndClientInfoSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = EndClientInfoSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = json.loads(request.data["form_data"])
        profile_photo = request.data.get("profile_photo")

        serializer = EndClientSerializer(data=data, context={"request": request})

        if serializer.is_valid():
            with transaction.atomic():
                instance = serializer.save()

                serializer = EndClientInfoSerializer(instance)
                email = data["email"]
                user_phone = data["phone"]
                name = data["name"]

                if profile_photo and hasattr(profile_photo, "read"):
                    instance.upload_profile_photo_presentation(profile_photo)
                    instance.save()

                instance.save()

                token = generate_forget_pass_token(email, user_phone, 30)

                context = {"name": name, "token": token, "email": email}
                email_thread = threading.Thread(target=self.send_email, args=(instance, context))
                email_thread.start()
                return Response(
                    {
                        "success": True,
                        "message": ("Reset Password Mail has been sent to registered email"),
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        else:
            errors_message = " ".join([", ".join(value) for value in serializer.errors.values()])
            return Response(
                {"success": False, "message": errors_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Try to get form_data from request body first, then from query parameters
        form_data = request.data.get("form_data")
        if not form_data:
            form_data = request.query_params.get("form_data")

        if not form_data:
            return Response(
                {"success": False, "message": "form_data is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = json.loads(form_data)
        except (json.JSONDecodeError, TypeError):
            return Response(
                {"success": False, "message": "Invalid JSON in form_data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile_photo = request.data.get("profile_photo")

        serializer = EndClientSerializer(instance, data=data, context={"request": request}, partial=True)

        if serializer.is_valid():
            comapny = serializer.save()

            if profile_photo and hasattr(profile_photo, "read"):
                instance.upload_profile_photo_presentation(profile_photo)
                instance.save()

            serializer = EndClientInfoSerializer(comapny)
            return Response(
                {"success": True, "data": serializer.data},
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
        serializer = EndClientInfoSerializer(instance)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.deleted_by = request.user
        instance.deleted_at = now()
        instance.save()
        return Response({"success": True, "message": "EndClient Delete"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path="profile-photo-delete")
    def profile_photo_delete(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.profile_photo:
            delete_uploaded_file(instance.profile_photo)
            instance.profile_photo = None
            instance.updated_by = request.user
            instance.updated_at = now()
            instance.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.end_client_photo_delete(instance, ip_address, request.user)
            return Response(
                {"success": True, "message": "EndClient Profile Photo Deleted Successfully."},
                status=status.HTTP_200_OK,
            )

        else:
            return Response(
                {"success": False, "message": "EndClient Profile Photo Not Found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_path="end_client-basic-info")
    def get_end_client_basic_info(self, request, pk=None):
        try:
            end_client = EndClient.objects.get(id=pk, deleted=False)

            data = {
                "profile_photo": end_client.profile_photo,
                "name": end_client.name,
                "email": end_client.email,
                "phone": end_client.phone,
            }
            return Response(data, status=200)

        except EndClient.DoesNotExist:
            return Response({"error": "EndClient not found."}, status=404)

    @action(detail=True, methods=["PATCH"], url_path="update-end-client-basic-info")
    def update_end_client_basic_info(self, request, pk=None):
        try:
            end_client = EndClient.objects.get(id=pk)
            form_data = json.loads(request.data.get("form_data", "{}"))

            # Extract all fields from form_data
            name = form_data.get("name")
            email = form_data.get("email")
            phone = form_data.get("phone")
            profile_photo = request.data.get("profile_photo", None)

            if name:
                end_client.name = name
            if email:
                end_client.email = email
            if phone:
                end_client.phone = phone

            if profile_photo and hasattr(profile_photo, "read"):
                end_client.upload_profile_photo_presentation(profile_photo)

            end_client.updated_by = request.user
            end_client.save()

            ip_address = get_client_ip(request)
            ActivityLog.log.update_end_client_basic_info(end_client, ip_address, request.user)

            # Update associated users
            users = User.objects.filter(end_client=end_client)
            for user in users:
                if name:
                    user.first_name = name
                if email:
                    user.email = email
                if phone:
                    user.phone = phone
                user.save()

            return Response({"message": "EndClient basic info updated successfully."}, status=200)

        except EndClient.DoesNotExist:
            return Response({"error": "EndClient not found."}, status=404)

        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON in form_data."}, status=400)

    @action(detail=True, methods=["PATCH"], url_path="change-end-client-password")
    def change_end_client_password(self, request, pk=None):
        try:
            end_client = EndClient.objects.get(id=pk)
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

            admin_group = CustomGroup.objects.filter(name="EndClient Admin", end_client=end_client).first()
            if admin_group:
                user = User.objects.filter(end_client=end_client, groups=admin_group).order_by("id").first()
            else:
                user = User.objects.filter(end_client=end_client, role__isnull=False).order_by("id").first()

            if not user:
                return Response(
                    {"success": False, "message": "Admin user not found for this EndClient."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            hashed_password = make_password(new_password)
            user.password = hashed_password
            user.save()
            ip_address = get_client_ip(request)
            ActivityLog.log.change_end_client_password(end_client, ip_address, request.user)

            return Response({"success": True, "message": "Password updated successfully."}, status=status.HTTP_200_OK)

        except EndClient.DoesNotExist:
            return Response({"success": False, "message": "EndClient not found."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["PATCH"], url_path="update-status")
    def update_end_client_status(self, request):
        end_client_id = request.data.get("end_client_id")
        new_status = request.data.get("status")

        if not end_client_id:
            return Response(
                {"success": False, "message": "EndClient ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not new_status:
            return Response({"success": False, "message": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate status
        valid_statuses = ["active", "inactive", "pending"]
        if new_status not in valid_statuses:
            return Response(
                {
                    "success": False,
                    "message": ("Invalid status. Must be one of: " + ", ".join(valid_statuses)),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            end_client = EndClient.objects.get(id=end_client_id, deleted=False)
            end_client.status = new_status
            end_client.updated_by = request.user
            end_client.save()

            is_active_flag = True if new_status == "active" else False
            User.objects.filter(end_client=end_client).update(status=new_status, is_active=is_active_flag)

            ip_address = get_client_ip(request)
            ActivityLog.log.update_end_client_status(end_client, ip_address, request.user)

            return Response(
                {"success": True, "message": "EndClient status updated successfully"}, status=status.HTTP_200_OK
            )

        except EndClient.DoesNotExist:
            return Response(
                {"success": False, "message": "EndClient not found or already deleted"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Error updating endclient status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EndClientArchiveViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = EndClient.objects.filter(deleted=True).order_by("-id")
    serializer_class = EndClientInfoSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "name",
        "email",
        "phone",
        "status",
        "profile_photo",
    ]

    ordering_fields = [
        "name",
        "email",
        "phone",
        "status",
        "profile_photo",
        "created_at",
        "updated_at",
    ]

    def create(self, request, *args, **kwargs):
        serializer = EndClientArchiveSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            serializer.save()

            message = "EndClient archived successfully" if count == 1 else "EndClients archived successfully"
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
            serializer = EndClientArchiveListSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = EndClientArchiveListSerializer(page, many=True)
            return self.get_paginated_response({"success": True, "data": serializer.data})
        serializer = EndClientArchiveListSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})


class EndClientRestoreViewSet(SearchOrderingFilter, ModelViewSet):
    queryset = EndClient.objects.filter(deleted=True).order_by("id")
    serializer_class = EndClientInfoSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def create(self, request, *args, **kwargs):
        serializer = EndClientRestoreSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            deleted_ids = (
                serializer.validated_data.get("deleted", [])
                if hasattr(serializer, "validated_data")
                else request.data.get("deleted", [])
            )
            count = len(deleted_ids) if isinstance(deleted_ids, list) else 1
            serializer.save()

            message = "EndClient restored successfully" if count == 1 else "EndClients restored successfully"
            return Response(
                {"success": True, "message": message},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
