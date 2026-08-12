from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.services import log_event
from user.models import AuthGroupPermissionsModel, CustomGroup, RoleFamily, User
from user.permissions import IsAdminOrProvider, is_admin_user
from user.user_auth import PROJECT_APP_LABELS, get_user_permissions
from utils.pagination import Pagination
from utils.role_permission import get_group_permission_by_user, parse_ids

from .serializers import CustomGroupSerializers, PermissionSerializers


def _resolve_permission_objects(values):
    """Resolve permission ids/codenames to Permission objects, or None if invalid."""
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]

    ids = []
    codenames = []
    for value in values:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            ids.append(value)
        elif isinstance(value, str) and value.strip():
            codenames.append(value.strip())
        else:
            return None

    permissions = []
    if ids:
        id_permissions = list(Permission.objects.filter(id__in=ids))
        if len(id_permissions) != len(set(ids)):
            return None
        permissions.extend(id_permissions)
    if codenames:
        codename_permissions = list(Permission.objects.filter(codename__in=codenames))
        if len(codename_permissions) != len(set(codenames)):
            return None
        permissions.extend(codename_permissions)
    return permissions


def _can_assign_permissions(user, permissions):
    """Non-admin users may only grant permissions they already possess."""
    if is_admin_user(user):
        return True
    owned = set(get_user_permissions(user))
    return all(f"{p.content_type.app_label}|{p.codename}" in owned for p in permissions)


def _get_owned_role_queryset(user, deleted=False):
    """Roles a user may manage: admins see all, others only roles they created.
    ``deleted=True`` targets archived roles for restore.
    """
    queryset = CustomGroup.objects.filter(deleted=deleted)
    if not is_admin_user(user):
        queryset = queryset.filter(created_by=user)
    return queryset


class AssignUserGroupViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    # Only assign is exposed; destroy() would cascade-revoke member permissions.
    http_method_names = ["post", "head", "options"]

    def create(self, request, *args, **kwargs):
        user_ids = parse_ids(request.data.get("user_id"))
        if user_ids is None:
            return Response(
                {"success": False, "message": "Invalid user_id or role_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user_ids:
            return Response(
                {"success": False, "message": "user_id must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role_id_list = parse_ids(request.data.get("role_id"))
        if role_id_list is None or len(role_id_list) != 1:
            return Response(
                {"success": False, "message": "Invalid user_id or role_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role_id = role_id_list[0]

        user_list = User.objects.filter(pk__in=user_ids, deleted=False)

        # Owners may only assign roles they created to users they created.
        if not is_admin_user(request.user):
            if request.user.user_type not in [
                User.Role.INSTITUTE,
                User.Role.SCHOOL_COLLEGE,
                User.Role.CORPORATE,
            ]:
                return Response(
                    {
                        "success": False,
                        "message": "Only organization users can assign roles",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Archived roles must be restored before assignment.
            if not _get_owned_role_queryset(request.user).filter(id=role_id).exists():
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if user_list.exclude(created_by=request.user).exists():
                return Response(
                    {
                        "success": False,
                        "message": "You can only assign roles to users you created",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            role = Group.objects.get(pk=role_id)
        except Group.DoesNotExist:
            return Response(
                {"success": False, "message": "Role does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not CustomGroup.objects.filter(id=role_id, deleted=False).exists():
            return Response(
                {"success": False, "message": "Role not found"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if len(user_list) != len(user_ids):
            return Response(
                {"success": False, "message": "Users do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for user in user_list:
            role.user_set.add(user)

        log_event(
            event="role.assigned",
            description=f"Assigned role {role.name} to {len(user_list)} user(s)",
            user=request.user,
            entity_type="role",
            entity_id=role_id,
            metadata={
                "role_id": role_id,
                "role_name": role.name,
                "user_ids": user_ids,
            },
            request=request,
        )

        return Response(
            {"success": True, "message": "User assigned to role"},
            status=status.HTTP_200_OK,
        )


class PermissionViewSet(ModelViewSet):
    queryset = Permission.objects.filter(
        content_type__app_label__in=PROJECT_APP_LABELS
    ).order_by("id")
    serializer_class = PermissionSerializers
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    # Read-only permission browser; writes are blocked.
    http_method_names = ["get", "patch", "head", "options"]

    def update(self, request, *args, **kwargs):
        return Response(
            {"success": False, "message": "Method not allowed"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    partial_update = update

    def get_queryset(self):
        queryset = super().get_queryset()
        if is_admin_user(self.request.user):
            return queryset
        return queryset.filter(
            Q(group__user=self.request.user) | Q(user=self.request.user)
        ).distinct()

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
            content_type__app_label=app_label, content_type__model=model_name
        )

        page = self.paginate_queryset(permission_list)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(permission_list, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(permission_list, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["PATCH"], url_path="role-wise-permission")
    def role_wise_permission(self, request, *args, **kwargs):
        role_id = request.data.get("role_id")

        if not role_id:
            return Response(
                {"success": False, "message": "Provide Valid Data"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_id_list = parse_ids(role_id)
        if not role_id_list:
            return Response(
                {"success": False, "message": "Invalid role_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        owned_roles = _get_owned_role_queryset(request.user).filter(pk__in=role_id_list)
        if is_admin_user(request.user):
            if not owned_roles.exists():
                return Response(
                    {"success": False, "message": "Role not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            if owned_roles.count() != len(set(role_id_list)):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        fetched_permissions = AuthGroupPermissionsModel.objects.filter(
            group_id__in=role_id_list
        ).order_by("-id")
        permission_ids = list(
            fetched_permissions.values_list("permission_id", flat=True)
        )
        permissions_by_id = {
            p.id: p
            for p in Permission.objects.filter(id__in=permission_ids).select_related(
                "content_type"
            )
        }
        groups_by_id = {
            g.group_ptr_id: g
            for g in CustomGroup.objects.filter(group_ptr_id__in=role_id_list)
        }

        permission_details = []
        for fetched in fetched_permissions:
            permission = permissions_by_id.get(fetched.permission_id)
            if permission is None:
                continue
            permission_info = PermissionSerializers(permission).data
            custom_group = groups_by_id.get(fetched.group_id)
            permission_info["role_id"] = fetched.group_id
            permission_info["role_name"] = (
                custom_group.group_name if custom_group else None
            )
            permission_details.append(permission_info)

        return Response(
            {"success": True, "data": permission_details}, status=status.HTTP_200_OK
        )

    def list(self, request, *args, **kwargs):
        role_name = self.request.query_params.get("role_name")

        if role_name:
            role = (
                _get_owned_role_queryset(self.request.user)
                .filter(Q(group_name=role_name) | Q(name=role_name))
                .order_by("id")
                .first()
            )
            if role is None:
                if is_admin_user(self.request.user):
                    return Response(
                        {"success": False, "message": "Role not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            permission_ids = AuthGroupPermissionsModel.objects.filter(
                group_id=role.id
            ).values_list("permission_id", flat=True)
            permission_list = PermissionSerializers(
                Permission.objects.filter(id__in=permission_ids).select_related(
                    "content_type"
                ),
                many=True,
            ).data
            return Response(
                {"success": True, "data": permission_list},
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
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class AssignPermissionGroupViewSet(ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    # Only assign is exposed; other routes would let providers mutate Permission rows.
    http_method_names = ["post", "head", "options"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        role_id = request.data.get("role_id")
        codename = request.data.get("codename")

        codename_list = codename if isinstance(codename, list) else [codename]
        codename_list = [str(c).strip() for c in codename_list if c and str(c).strip()]
        if not codename_list:
            return Response(
                {"success": False, "message": "codename must be a non-empty list."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            role_id = int(role_id)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "Invalid role_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Admins can assign to any role; owners only to roles they created.
        if not is_admin_user(request.user):
            if not _get_owned_role_queryset(request.user).filter(id=role_id).exists():
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            role = Group.objects.get(pk=role_id)
        except Group.DoesNotExist:
            return Response(
                {"success": False, "message": "Role does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not CustomGroup.objects.filter(id=role_id, deleted=False).exists():
            return Response(
                {"success": False, "message": "Role not found"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Resolve all codenames before writing (no partial grants).
        permissions_to_add = []
        for codename in codename_list:
            permission = Permission.objects.filter(codename=codename).first()
            if permission is None:
                return Response(
                    {
                        "success": False,
                        "message": f"Permission '{codename}' not found",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            permissions_to_add.append(permission)

        if not _can_assign_permissions(request.user, permissions_to_add):
            return Response(
                {
                    "success": False,
                    "message": "You can only assign permissions you possess",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        role.permissions.add(*permissions_to_add)

        log_event(
            event="role.permission_added",
            description=(
                f"Added {len(permissions_to_add)} permission(s) " f"to role {role.name}"
            ),
            user=request.user,
            entity_type="role",
            entity_id=role_id,
            metadata={
                "role_id": role_id,
                "role_name": role.name,
                "permissions": sorted(p.codename for p in permissions_to_add),
            },
            request=request,
        )

        permissions_data = PermissionSerializers(role.permissions.all(), many=True).data
        return Response(
            {
                "success": True,
                "message": "Permission assigned to role",
                "data": permissions_data,
            },
            status=status.HTTP_200_OK,
        )


class CreateGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [OrderingFilter, SearchFilter]
    ordering_fields = ["name", "sequence"]
    search_fields = ["name"]

    def get_permissions(self):
        perms = super().get_permissions()
        # Role writes are owner-only; read actions stay open.
        if self.action in ("create", "update", "partial_update", "destroy"):
            perms = perms + [IsAdminOrProvider()]
        return perms

    @action(detail=False, methods=["GET"], url_path="get-role-permission-by-user")
    def get_role_permission_by_user(self, request, *args, **kwargs):
        user_roles = Group.objects.filter(user=request.user).values_list(
            "id", flat=True
        )
        user_custom_roles = CustomGroup.objects.filter(group_ptr__in=user_roles)

        response = get_group_permission_by_user(user_custom_roles)

        return Response({"success": True, "data": response}, status=status.HTTP_200_OK)

    def get_queryset(self):
        # Archived roles are hidden from read paths (deleted=False convention).
        queryset = super().get_queryset().exclude(customgroup__deleted=True)
        search_param = self.request.query_params.get("search", None)
        ordering_param = self.request.query_params.get("ordering", None)

        if search_param:
            queryset = queryset.filter(name__icontains=search_param)

        if ordering_param:
            queryset = queryset.order_by(ordering_param)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not is_admin_user(request.user):
            queryset = queryset.filter(
                customgroup__in=_get_owned_role_queryset(request.user)
            )
        roles = list(
            queryset.prefetch_related(
                Prefetch(
                    "permissions",
                    queryset=Permission.objects.select_related("content_type"),
                )
            )
        )
        # Resolve CustomGroup rows in one query via the MTI group_ptr link.
        custom_groups = {
            cg.group_ptr_id: cg
            for cg in CustomGroup.objects.filter(
                group_ptr_id__in=[role.id for role in roles]
            ).select_related("role_family")
        }
        role_list = []

        for role in roles:
            custom_group = custom_groups.get(role.id)
            role_list.append(
                {
                    "role_id": role.id,
                    "role_name": (
                        custom_group.group_name if custom_group else role.name
                    ),
                    "sequence": custom_group.sequence if custom_group else None,
                    "role_family": (
                        {
                            "id": custom_group.role_family.id,
                            "name": custom_group.role_family.family_name,
                        }
                        if custom_group and custom_group.role_family
                        else None
                    ),
                    "permissions": PermissionSerializers(
                        role.permissions.all(), many=True
                    ).data,
                }
            )

        return Response({"success": True, "data": role_list}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Same ownership rule as update()/destroy().
        if not is_admin_user(request.user):
            if (
                not _get_owned_role_queryset(request.user)
                .filter(pk=instance.pk)
                .exists()
            ):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Same MTI lookup as list().
        custom_group = CustomGroup.objects.filter(group_ptr=instance).first()

        role_data = {
            "role_id": instance.id,
            "role_name": (custom_group.group_name if custom_group else instance.name),
            "sequence": custom_group.sequence if custom_group else None,
            "role_family": (
                {
                    "id": custom_group.role_family.id,
                    "name": custom_group.role_family.family_name,
                }
                if custom_group and custom_group.role_family
                else None
            ),
            "permissions": PermissionSerializers(
                instance.permissions.all(), many=True
            ).data,
        }

        return Response({"success": True, "data": role_data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="get-role-permissions")
    def get_role_permissions(self, request, *args, **kwargs):
        role_ids_param = request.query_params.get("role_ids")
        role_id_param = request.query_params.get("role_id")

        if not role_ids_param and not role_id_param:
            return Response(
                {
                    "success": False,
                    "message": "Please provide role_id or role_ids",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_ids = parse_ids(role_ids_param or role_id_param)
        if not role_ids:
            return Response(
                {"success": False, "message": "Invalid role id(s)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        custom_roles = _get_owned_role_queryset(request.user).filter(pk__in=role_ids)
        if is_admin_user(request.user):
            if not custom_roles.exists():
                return Response(
                    {"success": False, "message": "Role not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Non-admins may only read roles they created; reject partial matches.
            if custom_roles.count() != len(set(role_ids)):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        response = get_group_permission_by_user(custom_roles)

        return Response({"success": True, "data": response}, status=status.HTTP_200_OK)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        role_name = request.data.get("role_name")
        role_family = request.data.get("role_family")
        permissions_input = request.data.get("permissions", [])

        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except (RoleFamily.DoesNotExist, TypeError, ValueError):
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not role_name or not str(role_name).strip():
            return Response(
                {
                    "success": False,
                    "message": "Role name should contain only characters",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        role_exists = CustomGroup.objects.filter(
            group_name=role_name, created_by=request.user
        ).exists()
        if role_exists:
            return Response(
                {"success": False, "message": "Role name already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve permissions before any write (codenames canonical, ids accepted).
        permissions = _resolve_permission_objects(permissions_input)
        if permissions is None:
            return Response(
                {
                    "success": False,
                    "message": "Invalid permission id(s) or codename(s).",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not _can_assign_permissions(request.user, permissions):
            return Response(
                {
                    "success": False,
                    "message": "You can only assign permissions you possess",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        custom_group = CustomGroup(
            name=role_name,
            group_name=role_name,
            role_family=role_family_instance,
            created_by=request.user,
        )
        custom_group.save()
        custom_group.user_set.add(request.user)
        if permissions:
            custom_group.permissions.set(permissions)

        log_event(
            event="role.created",
            description=f"Created role {custom_group.group_name}",
            user=request.user,
            entity_type="role",
            entity_id=custom_group.id,
            metadata={
                "role_id": custom_group.id,
                "role_name": custom_group.group_name,
                "role_family_id": (
                    role_family_instance.id if role_family_instance else None
                ),
                "permissions": sorted(
                    custom_group.permissions.values_list("codename", flat=True)
                ),
            },
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": "Role created and permissions assigned",
                "data": {
                    "role_id": custom_group.id,
                    "role_name": custom_group.group_name,
                    "sequence": custom_group.sequence,
                    "role_family": (
                        {
                            "id": custom_group.role_family.id,
                            "name": custom_group.role_family.family_name,
                        }
                        if custom_group.role_family
                        else None
                    ),
                    "permissions": PermissionSerializers(
                        custom_group.permissions.all(), many=True
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        role = self.get_object()
        role_name = request.data.get("role_name")
        role_family = request.data.get("role_family")
        permissions_input = request.data.get("permissions")
        role_id = kwargs.get("pk")

        if not is_admin_user(request.user):
            if not _get_owned_role_queryset(request.user).filter(id=role_id).exists():
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        role_family_instance = None
        if role_family:
            try:
                role_family_instance = RoleFamily.objects.get(id=role_family)
            except (RoleFamily.DoesNotExist, TypeError, ValueError):
                return Response(
                    {"success": False, "message": "Role Family Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Plain Groups without a CustomGroup child cannot be role-edited.
        role_instance = CustomGroup.objects.filter(pk=role_id).first()
        if role_instance is None:
            return Response(
                {"success": False, "message": "Role not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Identity fields only update on non-empty values (DRF PATCH semantics).
        has_identity_update = False
        if "role_name" in request.data and role_name:
            role_exists = (
                CustomGroup.objects.filter(
                    group_name=role_name, created_by=request.user
                )
                .exclude(pk=role_id)
                .exists()
            )
            if role_exists:
                return Response(
                    {"success": False, "message": "Role name already exists"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            role_instance.name = role_name
            role_instance.group_name = role_name
            has_identity_update = True
        if "role_family" in request.data and role_family:
            role_instance.role_family = role_family_instance
            has_identity_update = True
        if has_identity_update:
            role_instance.updated_by = request.user
            role_instance.save()

        # Permissions only change when the key is present; diff computed only then.
        permission_diff = {"added_permissions": [], "removed_permissions": []}
        if "permissions" in request.data and permissions_input is not None:
            before_codenames = set(role.permissions.values_list("codename", flat=True))
            permissions = _resolve_permission_objects(permissions_input)
            if permissions is None:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid permission id(s) or codename(s).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not _can_assign_permissions(request.user, permissions):
                return Response(
                    {
                        "success": False,
                        "message": "You can only assign permissions you possess",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            role.permissions.set(permissions)
            after_codenames = set(role.permissions.values_list("codename", flat=True))
            permission_diff = {
                "added_permissions": sorted(after_codenames - before_codenames),
                "removed_permissions": sorted(before_codenames - after_codenames),
            }

        log_event(
            event="role.updated",
            description=f"Updated role {role_instance.group_name}",
            user=request.user,
            entity_type="role",
            entity_id=role_instance.id,
            metadata={
                "role_id": role_instance.id,
                "role_name": role_instance.group_name,
                "role_family_id": role_instance.role_family_id,
                "added_permissions": permission_diff["added_permissions"],
                "removed_permissions": permission_diff["removed_permissions"],
            },
            request=request,
        )

        return Response(
            {
                "success": True,
                "message": "Role updated",
                "data": {
                    "role_id": role_instance.id,
                    "role_name": role_instance.group_name,
                    "sequence": (
                        role_instance.sequence if role_instance.sequence else None
                    ),
                    "role_family": (
                        {
                            "id": role_instance.role_family.id,
                            "name": role_instance.role_family.family_name,
                        }
                        if role_instance.role_family
                        else None
                    ),
                    "permissions": PermissionSerializers(
                        role.permissions.all(), many=True
                    ).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if not is_admin_user(request.user):
            if (
                not _get_owned_role_queryset(request.user)
                .filter(id=instance.pk)
                .exists()
            ):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Soft delete - hard delete would cascade-revoke member permissions.
        custom_group = CustomGroup.objects.filter(pk=instance.pk).first()
        if custom_group is None:
            # Plain groups without a CustomGroup child report 404, not 500.
            return Response(
                {"success": False, "message": "Role not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        custom_group.deleted = True
        custom_group.save(update_fields=["deleted"])
        log_event(
            event="role.deleted",
            description=f"Deleted role {custom_group.group_name or custom_group.name}",
            user=request.user,
            entity_type="role",
            entity_id=instance.pk,
            metadata={
                "role_id": instance.pk,
                "role_name": custom_group.group_name or custom_group.name,
            },
            request=request,
        )
        return Response(
            {"success": True, "message": "Role Deleted"}, status=status.HTTP_200_OK
        )


class DeleteGroupWithPermissionsViewSet(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = CustomGroupSerializers
    permission_classes = [IsAuthenticated, IsAdminOrProvider]
    authentication_classes = [JWTAuthentication]
    pagination_class = Pagination
    # Only archive/restore/archived-list are exposed; destroy() would cascade-revoke permissions.
    http_method_names = ["post", "get", "head", "options"]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        role_ids = parse_ids(request.data.get("role_ids"))
        if role_ids is None:
            return Response(
                {
                    "success": False,
                    "message": "Invalid role_ids.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not role_ids:
            return Response(
                {
                    "success": False,
                    "message": "No role IDs provided for deletion.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_admin_user(request.user):
            if _get_owned_role_queryset(request.user).filter(
                id__in=role_ids
            ).count() != len(set(role_ids)):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        roles = CustomGroup.objects.filter(id__in=role_ids)
        for role in roles:
            role.deleted = True
            role.save()

        log_event(
            event="role.archived",
            description=f"Archived {roles.count()} role(s)",
            user=request.user,
            entity_type="role",
            entity_id=None,
            metadata={"role_ids": role_ids, "count": roles.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Roles archived successfully"},
            status=status.HTTP_200_OK,
        )

    @transaction.atomic
    @action(detail=False, methods=["post"], url_path="restore")
    def restore_roles(self, request, *args, **kwargs):
        role_ids = parse_ids(request.data.get("role_ids"))
        if role_ids is None:
            return Response(
                {
                    "success": False,
                    "message": "Invalid role_ids.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not role_ids:
            return Response(
                {
                    "success": False,
                    "message": "No role IDs provided for deletion.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not is_admin_user(request.user):
            if _get_owned_role_queryset(request.user, deleted=True).filter(
                id__in=role_ids
            ).count() != len(set(role_ids)):
                return Response(
                    {
                        "success": False,
                        "message": "Role not found or not owned by you",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        roles = CustomGroup.objects.filter(id__in=role_ids)
        for role in roles:
            role.deleted = False
            role.save()

        log_event(
            event="role.restored",
            description=f"Restored {roles.count()} role(s)",
            user=request.user,
            entity_type="role",
            entity_id=None,
            metadata={"role_ids": role_ids, "count": roles.count()},
            request=request,
        )

        return Response(
            {"success": True, "message": "Roles restored successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="archived")
    def archived_list(self, request, *args, **kwargs):
        user = request.user
        archived_roles = (
            _get_owned_role_queryset(user, deleted=True)
            .select_related("role_family")
            .prefetch_related(
                Prefetch(
                    "permissions",
                    queryset=Permission.objects.select_related("content_type"),
                )
            )
            .order_by("-sequence")
        )
        queryset = self.filter_queryset(archived_roles)

        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        items = queryset if no_pagination or page is None else page

        role_list = [
            {
                "role_id": role.id,
                "role_name": role.group_name,
                "sequence": role.sequence,
                "role_family": (
                    {
                        "id": role.role_family.id,
                        "name": role.role_family.family_name,
                    }
                    if role.role_family
                    else None
                ),
                "permissions": PermissionSerializers(
                    role.permissions.all(), many=True
                ).data,
            }
            for role in items
        ]

        if no_pagination:
            return Response({"success": True, "data": role_list})
        if page is not None:
            return self.get_paginated_response({"success": True, "data": role_list})

        return Response({"success": True, "data": role_list}, status=status.HTTP_200_OK)
