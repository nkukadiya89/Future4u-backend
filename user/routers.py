from rest_framework.routers import DefaultRouter, path

from user.admin_user_views import (
    AdminCorporateViewSet,
    AdminInstituteViewSet,
    AdminSchoolCollegeViewSet,
    AdminStudentViewSet,
    AdminUserArchiveViewSet,
    AdminWorkingProfessionalViewSet,
)
from user.email_phone_verify import VerifiedOTPViewSet
from user.group_and_permission import (
    AssignPermissionGroupViewSet,
    AssignUserGroupViewSet,
    CreateGroupWithPermissionsViewSet,
    DeleteGroupWithPermissionsViewSet,
    PermissionViewSet,
)
from user.organization_professional_views import OrganizationProfessionalViewSet
from user.resend_password_reset import ResendPasswordResetViewSet
from user.organization_staff_views import OrganizationStaffViewSet
from user.student_organization_views import OrganizationStudentViewSet
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
user_router.register(
    "roles", CreateGroupWithPermissionsViewSet, basename="roles"
)
user_router.register(
    "role-archive",
    DeleteGroupWithPermissionsViewSet,
    basename="role_archive",
)
user_router.register(
    "assign-role", AssignUserGroupViewSet, basename="assign_role"
)
user_router.register(
    "assign-role-permission",
    AssignPermissionGroupViewSet,
    basename="assign_role_permission",
)
user_router.register("permissions", PermissionViewSet, basename="permissions")

user_router.register("auth", AuthViewSet, basename="auth")
user_router.register("admin-student-users", AdminStudentViewSet, basename="admin_users")
user_router.register(
    "admin-school-colleges-users",
    AdminSchoolCollegeViewSet,
    basename="admin_school_colleges_users",
)
user_router.register(
    "admin-institute-users", AdminInstituteViewSet, basename="admin_institute_users"
)
user_router.register(
    "admin-corporate-users", AdminCorporateViewSet, basename="admin_corporate_users"
)
user_router.register(
    "admin-working-professional-users",
    AdminWorkingProfessionalViewSet,
    basename="admin_working_professional_users",
)
user_router.register(
    "admin-users-archive",
    AdminUserArchiveViewSet,
    basename="admin_users_archive",
)
user_router.register(
    "organization-students",
    OrganizationStudentViewSet,
    basename="organization_students",
)
user_router.register(
    "organization-staff",
    OrganizationStaffViewSet,
    basename="organization_staff",
)

user_router.register(
    "organization-professionals",
    OrganizationProfessionalViewSet,
    basename="organization_professionals",
)
user_router.register("users", UserListViewSet, basename="users")
