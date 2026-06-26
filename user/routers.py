from rest_framework.routers import DefaultRouter, path

from user.email_phone_verify import VerifiedOTPViewSet
from user.group_and_permission import (
    AssignPermissionGroupViewSet,
    AssignUserGroupViewSet,
    CreateGroupWithPermissionsViewSet,
    DeleteGroupWithPermissionsViewSet,
    GetAllPermissionViewSet,
    GetGroupPermissionViewSet,
    GroupViewSet,
    PermissionViewSet,
)
from user.admin_user_views import AdminStudentViewSet
from user.resend_password_reset import ResendPasswordResetViewSet
from user.user_type_views import AuthViewSet
from user.views import (
    ForgetPasswordViewSet,
    ForgotPasswordViewSet,
    LoginWithEmailOtpViewset,
    ResetPasswordViewSet,
    RoleFamilyViewSet,
    UserDetailsViewSet,
    UserListViewSet,
    VerifyEmailOtpAndGiveTokenViewset,
    VerifyOtpViewSet,
)

user_router = DefaultRouter()
user_router.register(
    "forgot-password", ForgetPasswordViewSet, basename="forget_password"
)
user_router.register(
    r"reset-password/(?P<token>[\w\.-]+)",
    ResetPasswordViewSet,
    basename="reset_password",
)
user_router.register(
    r"forgot-password/(?P<token>[\w\.-]+)",
    ForgotPasswordViewSet,
    basename="forgot_password_token",
)
user_router.register("verify-otp", VerifyOtpViewSet, basename="verify_otp")
user_router.register("user-detail", UserDetailsViewSet, basename="user_detail")
user_router.register(
    "resend-password-reset",
    ResendPasswordResetViewSet,
    basename="resend_password_reset",
)
user_router.register(
    "email-otp-login", LoginWithEmailOtpViewset, basename="Login_with_email_otp"
)
user_router.register(
    "verify-otp-send-token",
    VerifyEmailOtpAndGiveTokenViewset,
    basename="verify_otp_give_token",
)
user_router.register("role-family", RoleFamilyViewSet, basename="role_family")
user_router.register("verified-otp", VerifiedOTPViewSet, basename="verified-otp")
user_router.register("create-group", GroupViewSet, basename="create_new_group")
user_router.register("get-group", GroupViewSet, basename="list_group")
user_router.register(
    "assign-user-group", AssignUserGroupViewSet, basename="assign_user_group"
)
user_router.register(
    "create-group-permissions",
    CreateGroupWithPermissionsViewSet,
    basename="create_group_with_permissions",
)
user_router.register(
    "delete-group-permissions",
    DeleteGroupWithPermissionsViewSet,
    basename="delete_group_with_permissions",
)
user_router.register(
    "get-all-permission-list", GetAllPermissionViewSet, basename="list_all_permissions"
)
user_router.register("list-permission", PermissionViewSet, basename="list_permission")
user_router.register(
    "get-group-permission", GetGroupPermissionViewSet, basename="get_group_permission"
)
user_router.register(
    "assign-permission-group",
    AssignPermissionGroupViewSet,
    basename="assign_permission_group",
)

user_router.register("auth", AuthViewSet, basename="auth")
user_router.register("admin-student-users", AdminStudentViewSet, basename="admin_users")
user_router.register("users", UserListViewSet, basename="users")
