from django.contrib.auth.models import Group, Permission
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.models import AuthGroupPermissionsModel, CustomGroup, RoleFamily, User
from utils.pagination import Pagination
from utils.role_permission import (
    get_group_permission_by_user,
    get_permission_by_group_ids,
    get_purticlare_permission,
)

from .serializers import CustomGroupSerializers, PermissionSerializers


class GroupViewSet(ModelViewSet):
    queryset = Group.objects.all().order_by("-id")
    serializer_class = CustomGroupSerializers
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["id", "name", "sequence"]
    ordering_fields = ["id", "name", "sequence"]

    def list(self, request, *args, **kwargs):
        user = request.user
        no_pagination = self.request.query_params.get("no_pagination")
        company_id = self.request.query_params.get("company_id")
        partner_company_id = self.request.query_params.get("partner_company_id")

        # partner_company / end_client groups removed from the data model
        if partner_company_id:
            return Response(
                {
                    "success": False,
                    "message": "partner company groups are not available anymore",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if company_id:
            queryset = self.filter_queryset(
                CustomGroup.objects.filter(company=company_id, deleted=False).order_by(
                    "-id"
                )
            )

        else:
            queryset = self.filter_queryset(
                CustomGroup.objects.filter(
                    created_by=user.id,
                    company__isnull=True,
                    deleted=False,
                ).order_by("-id")
            )

        self.pagination_class.page_size = int(request.query_params.get("pagesize", 10))
        page = self.paginate_queryset(queryset)

        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return Response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = CustomGroupSerializers(data=data)

        if serializer.is_valid():
            serializer.validated_data["created_by"] = request.user
            serializer.save()

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @transaction.atomic
    @action(detail=False, methods=["get"], url_path="archive-group-permissions-list")
    def archive_group_permissions_list(self, request, *args, **kwargs):
        user = request.user
        archive_group_list = CustomGroup.objects.filter(
            created_by=user.id, deleted=True
        ).order_by("-sequence")
        queryset = self.filter_queryset(archive_group_list)
        excluded_group_ids = [1, 2, 3]
        queryset = queryset.exclude(id__in=excluded_group_ids)

        self.pagination_class.page_size = int(request.query_params.get("pagesize", 10))
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
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        instance = self.get_object()

        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            instance.save()
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AssignUserGroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers

    def create(self, request, *args, **kwargs):
        user_ids = request.data.get("user_id")
        user_list = User.objects.filter(pk__in=user_ids)
        group_id = request.data.get("group_id")
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            return Response(
                {"success": False, "message": "Group does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(user_list) != len(user_ids):
            return Response(
                {"success": False, "message": "Users do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for user in user_list:
            group.user_set.add(user)

        return Response(
            {"success": True, "message": "User assigned to group"},
            status=status.HTTP_200_OK,
        )


class PermissionViewSet(ModelViewSet):
    queryset = Permission.objects.filter(content_type_id__gt=5).order_by("id")
    serializer_class = PermissionSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @action(
        detail=False,
        methods=["GET"],
        url_path="get-purticlare-permission",
        permission_classes=[AllowAny],
    )
    def get_purticlare_permission(self, request, *args, **kwargs):
        content_types = self.request.query_params.get("content_types")
        model_names = self.request.query_params.get("model_names")
        group_id = self.request.query_params.get("group_id")
        company_id = self.request.query_params.get("company_id")
        partner_company_id = self.request.query_params.get("partner_company_id")
        end_client_id = self.request.query_params.get("end_client_id")

        if not content_types:
            return Response({"success": False, "message": "Content Type Not Found"})

        if not model_names:
            return Response({"success": False, "message": "Model Name Not Found"})

        response = get_purticlare_permission(
            content_types,
            model_names,
            group_id,
            company_id,
            partner_company_id,
            end_client_id,
        )
        return Response({"success": True, "data": response}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="model-wise-permission")
    def model_wise_permission(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        app_label = self.request.query_params.get("app_label")
        model_name = self.request.query_params.get("model_name")

        if not app_label:
            return Response({"success": False, "message": "App Label Not Found"})

        if not model_name:
            return Response({"success": False, "message": "Model Name Not Found"})

        permission_list = queryset.filter(
            content_type=app_label, content_type__model=model_name
        )

        page = self.paginate_queryset(permission_list)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(permission_list, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["PATCH"], url_path="group-wise-permission")
    def group_wise_permission(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids")
        group_id = request.data.get("group_id")
        company_id = request.data.get("company_id")
        partner_company_id = request.data.get("partner_company_id")
        role_name = request.data.get("role_name")

        if group_ids:
            user_assigned_groups = None
            user_assigned_permissions = None
            try:
                if role_name:
                    role_permission = Group.objects.get(name=role_name)
                    user_assigned_groups = role_permission
                elif company_id:
                    User.objects.get(company=company_id)
                    user_assigned_groups = Group.objects.get(name="Company Admin")
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "partner company groups are not available anymore",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except Group.DoesNotExist:
                return Response(
                    {"success": False, "message": "Group not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response = get_permission_by_group_ids(
                group_ids, user_assigned_groups, user_assigned_permissions
            )
            return Response(
                {"success": True, "data": response}, status=status.HTTP_200_OK
            )

        elif group_id:
            fetched_permissions = AuthGroupPermissionsModel.objects.filter(
                group_id__in=group_id
            ).order_by("-id")

            permission_details = []
            for get_permission in fetched_permissions:
                codename = Permission.objects.get(
                    id=get_permission.permission.id
                ).codename
                custom_group = CustomGroup.objects.get(
                    group_ptr=get_permission.group.id
                )

                permission_info = {
                    "id": get_permission.id,
                    "group_id": get_permission.group.id,
                    "group_name": custom_group.group_name,
                    "content_type": get_permission.permission.content_type.id,
                    "model_name": (
                        get_permission.permission.content_type.model.capitalize()
                    ),
                    "codename": codename,
                }
                permission_details.append(permission_info)

            return Response(
                {"success": True, "data": permission_details}, status=status.HTTP_200_OK
            )

        else:
            return Response(
                {"success": False, "message": "Provide Valid Data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def list(self, request, *args, **kwargs):
        group_name = self.request.query_params.get("group_name")

        if group_name:
            permission_list = []
            permission_by_group = AuthGroupPermissionsModel.objects.filter(
                group__name=group_name
            )

            for permissions in permission_by_group:
                codename = Permission.objects.get(id=permissions.permission.id)
                permission_detail = {
                    "id": permissions.permission.id,
                    "name": permissions.permission.name,
                    "codename": codename.codename,
                    "content_type_id": permissions.permission.content_type.id,
                    "model": permissions.permission.content_type.model.capitalize(),
                }
                permission_list.append(permission_detail)
            return Response(
                {
                    "success": True,
                    "data": permission_list,
                },
                status=status.HTTP_200_OK,
            )

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class GetGroupPermissionViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        data = {}
        group_id = self.kwargs.get("id")
        try:
            group = Group.objects.get(pk=group_id)
        except Group.DoesNotExist:
            data["total_record"] = 0
            data["success"] = False
            data["message"] = "Group not found"
            data["data"] = []
            return Response(data=data, status=status.HTTP_404_NOT_FOUND)

        permission_list = {}

        for permission in group.permissions.all():
            app_label = permission.content_type.app_label
            codename = permission.codename

            if app_label in permission_list:
                permission_list[app_label].append(codename)
            else:
                permission_list[app_label] = [codename]

        data["total_record"] = len(permission_list)
        data["success"] = True
        data["message"] = "OK"
        data["data"] = permission_list
        return Response(data=data, status=status.HTTP_200_OK)


class AssignPermissionGroupViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers

    def create(self, request, *args, **kwargs):
        group_id = request.data.get("group_id")
        codename_list = list(request.data.get("codename"))

        group = Group.objects.get(pk=group_id)
        for codename in codename_list:
            code_id = (
                Permission.objects.filter(codename=codename).values("id")[0].get("id")
            )
            group.permissions.add(code_id)

        group_permission = Permission.objects.filter(group=group)
        permission_list = {}
        for permission in group_permission:
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Permission assigned to group",
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )


class GetAllPermissionViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CreateGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name", "sequence"]
    search_fields = ["name"]

    @action(detail=False, methods=["GET"], url_path="get-group-permission-by-user")
    def get_group_permission_by_user(self, request, *args, **kwargs):
        login_user = request.user  # Better: use request.user directly

        # Get all groups the user belongs to
        user_groups = Group.objects.filter(user=login_user).values_list("id", flat=True)

        # Company logic removed - users are now standalone
        # TODO: Implement alternative group exclusion logic
        exclude_group_names = []  # No exclusion for now

        # Get user's custom groups, excluding the admin role specific to their type
        user_custom_groups = CustomGroup.objects.filter(
            group_ptr__in=user_groups
        ).exclude(group_ptr__name__in=exclude_group_names)

        # Optional: Get the excluded admin group (if needed for logic)
        excluded_admin_groups = CustomGroup.objects.filter(
            group_ptr__name__in=exclude_group_names
        )

        # Call your helper function (make sure it exists and works correctly)
        response = get_group_permission_by_user(
            user_custom_groups, excluded_admin_groups
        )

        return Response(
            {"success": True, "response": response}, status=status.HTTP_200_OK
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        search_param = self.request.query_params.get("search", None)
        ordering_param = self.request.query_params.get("ordering", None)

        if search_param:
            queryset = queryset.filter(name__icontains=search_param)

        if ordering_param:
            queryset = queryset.order_by(ordering_param)

        return queryset

    def list(self, request, *args, **kwargs):
        groups = self.get_queryset()
        group_list = []

        for group in groups:
            permissions = [
                {
                    "id": permission.id,
                    "permission": (
                        f"{permission.content_type.app_label}| {permission.name}"
                    ),
                }
                for permission in group.permissions.all()
            ]

            custom_group = CustomGroup.objects.filter(group_name=group).first()
            group_list.append(
                {
                    "group_id": group.id,
                    "group_name": custom_group.group_name,
                    "sequence": custom_group.sequence if custom_group else None,
                    "permissions": permissions,
                }
            )

        return Response(
            {"success": True, "response": group_list}, status=status.HTTP_200_OK
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        permissions = [
            {
                "id": permission.id,
                "permission": f"{permission.content_type.app_label} | {permission.name}",
            }
            for permission in instance.permissions.all()
        ]

        custom_group = CustomGroup.objects.filter(name=instance).first()

        group_data = {
            "group_id": instance.id,
            "group_name": custom_group.group_name,
            "role_family": (
                custom_group.role_family.id if custom_group.role_family else None
            ),
            "family_name": (
                custom_group.role_family.family_name
                if custom_group.role_family
                else None
            ),
            "sequence": custom_group.sequence if custom_group else None,
            "permissions": permissions,
        }

        return Response(
            {"success": True, "response": group_data}, status=status.HTTP_200_OK
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        group_name = request.data.get("group_name")
        role_family = request.data.get("role_family")
        permission_ids = request.data.get("permissions", [])
        company_id = request.data.get("company")
        partner_company_id = request.data.get("partner_company")
        end_client_id = request.data.get("end_client")

        # group = CustomGroup.objects.filter(group_name=group_name).exists()
        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except RoleFamily.DoesNotExist:
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if company_id:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, company_id=company_id
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the CustomGroup instance, which will automatically assign a sequence
            if group_name and group_name.replace(" ", "").isalpha():
                custom_group = CustomGroup(
                    name="company_" + str(company_id) + "_" + group_name,
                    group_name=group_name,
                    role_family=role_family_instance,
                    company_id=company_id,
                    created_by=request.user,
                )
                custom_group.save()
                user = User.objects.get(company=company_id).id
                custom_group.user_set.add(user)

            else:
                return Response(
                    {
                        "success": False,
                        "message": "Group name should contain only characters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif partner_company_id:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, partner_company_id=partner_company_id
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the CustomGroup instance, which will automatically assign a sequence
            if group_name and group_name.replace(" ", "").isalpha():
                custom_group = CustomGroup(
                    name="partner_company_"
                    + str(partner_company_id)
                    + "_"
                    + group_name,
                    group_name=group_name,
                    role_family=role_family_instance,
                    partner_company_id=partner_company_id,
                    created_by=request.user,
                )
                custom_group.save()
                user = User.objects.get(
                    partner_company=partner_company_id, company__isnull=True
                ).id
                custom_group.user_set.add(user)

            else:
                return Response(
                    {
                        "success": False,
                        "message": "Group name should contain only characters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif end_client_id:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, end_client_id=end_client_id
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Create the CustomGroup instance, which will automatically assign a sequence
            if group_name and group_name.replace(" ", "").isalpha():
                custom_group = CustomGroup(
                    name="end_client_" + str(end_client_id) + "_" + group_name,
                    group_name=group_name,
                    role_family=role_family_instance,
                    end_client_id=end_client_id,
                    created_by=request.user,
                )
                custom_group.save()
                user = User.objects.get(
                    end_client=end_client_id,
                    company__isnull=True,
                    partner_company__isnull=True,
                ).id
                custom_group.user_set.add(user)

            else:
                return Response(
                    {
                        "success": False,
                        "message": "Group name should contain only characters",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            group_exists = CustomGroup.objects.filter(
                group_name=group_name, created_by=request.user
            ).exists()
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            custom_group = CustomGroup(
                name=group_name,
                group_name=group_name,
                created_by=request.user,
            )
            custom_group.save()
            user = User.objects.get(id=request.user.id).id
            custom_group.user_set.add(user)

        # Create the CustomGroup instance, which will automatically assign a sequence

        permissions = Permission.objects.filter(id__in=permission_ids)
        custom_group.permissions.set(permissions)

        permission_list = {}
        for permission in custom_group.permissions.all():
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Group created and Permission assigned to Group",
                "id": custom_group.id,
                "group_name": group_name,
                "sequence": custom_group.sequence,
                "role_family": (
                    custom_group.role_family.family_name
                    if custom_group.role_family
                    else None
                ),
                "company": company_id,
                "partner_company": partner_company_id,
                "end_client": end_client_id,
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        group = self.get_object()
        group_name = request.data.get("group_name")
        role_family = request.data.get("role_family")
        permission_ids = request.data.get("permissions", [])
        company_id = request.data.get("company")
        partner_company_id = request.data.get("partner_company")
        end_client_id = request.data.get("end_client")
        group_id = kwargs.get("pk")

        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except RoleFamily.DoesNotExist:
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        group_instance = CustomGroup.objects.get(pk=group_id)
        if company_id:
            group_exists = (
                CustomGroup.objects.filter(group_name=group_name, company_id=company_id)
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {
                        "success": False,
                        "message": "Role name already exists with your Company",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group_instance.name = "company_" + str(company_id) + "_" + group_name
            group_instance.group_name = group_name
            group_instance.role_family = role_family_instance
            group_instance.company_id = company_id
            group_instance.updated_by = request.user
            group_instance.save()

        elif partner_company_id:
            group_exists = (
                CustomGroup.objects.filter(
                    group_name=group_name, partner_company_id=partner_company_id
                )
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {
                        "success": False,
                        "message": "Role name already exists with your Partner Company",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group_instance.name = (
                "partner_company_" + str(partner_company_id) + "_" + group_name
            )
            group_instance.group_name = group_name
            group_instance.role_family = role_family_instance
            group_instance.partner_company_id = partner_company_id
            group_instance.updated_by = request.user
            group_instance.save()

        elif end_client_id:
            group_exists = (
                CustomGroup.objects.filter(
                    group_name=group_name, end_client_id=end_client_id
                )
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {
                        "success": False,
                        "message": "Role name already exists with your Partner Company",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            group_instance.name = "end_client_" + str(end_client_id) + "_" + group_name
            group_instance.group_name = group_name
            group_instance.role_family = role_family_instance
            group_instance.end_client_id = end_client_id
            group_instance.updated_by = request.user
            group_instance.save()

        else:
            group_exists = (
                CustomGroup.objects.filter(
                    group_name=group_name, created_by=request.user
                )
                .exclude(pk=group_id)
                .exists()
            )
            if group_exists:
                return Response(
                    {"success": False, "message": "Group name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            group_instance.name = group_name
            group_instance.group_name = group_name
            group_instance.updated_by = request.user
            group_instance.save()

        if permission_ids:
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)

        permission_list = {}
        for permission in group.permissions.all():
            if permission.content_type.app_label in permission_list:
                permission_name = permission_list[permission.content_type.app_label]
                permission_list[permission.content_type.app_label] = ",".join(
                    [permission_name, permission.name.split(" ")[1]]
                )
            else:
                permission_list[permission.content_type.app_label] = (
                    permission.name.split(" ")[1]
                )

        return Response(
            {
                "success": True,
                "message": "Group updated and Permission assigned to Group",
                "id": group_instance.id,
                "group_name": group_instance.group_name,
                "sequence": (
                    group_instance.sequence if group_instance.sequence else None
                ),
                "role_family": (
                    group_instance.role_family.family_name
                    if group_instance.role_family
                    else None
                ),
                "company": company_id,
                "partner_company": partner_company_id,
                "end_client": end_client_id,
                "response": permission_list,
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        instance.save()
        return Response(
            {"success": True, "message": "Role Deleted"}, status=status.HTTP_200_OK
        )


class DeleteGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids", [])

        if not group_ids:
            return Response(
                {"message": "No group IDs provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        groups = CustomGroup.objects.filter(id__in=group_ids)
        for group in groups:
            group.deleted = True
            group.save()

        return Response(
            {"success": True, "message": "Groups Archive successfully"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="restore-group-permissions")
    def restore_group_permissions(self, request, *args, **kwargs):
        group_ids = request.data.get("group_ids", [])

        if not group_ids:
            return Response(
                {"message": "No group IDs provided for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        groups = CustomGroup.objects.filter(id__in=group_ids)
        for group in groups:
            group.deleted = False
            group.save()

        return Response(
            {"success": True, "message": "Groups Restored successfully"},
            status=status.HTTP_200_OK,
        )
