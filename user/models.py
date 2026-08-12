import os

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.core.files.storage import default_storage
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from company.models import Company
from utils.aws_file_upload import delete_uploaded_file, upload_file_to_bucket


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """User model."""

    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("inactive", "inactive"),
    )

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent / Guardian"
        PROFESSIONAL = "working_professional", "Working Professional"
        SCHOOL_COLLEGE = "school_college", "School / College"
        INSTITUTE = "institute", "Institute / Course Provider"
        CORPORATE = "corporate", "Corporate / Employer"
        SUPER_ADMIN = "super_admin", "Super Admin"

    username = models.CharField(max_length=60, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, default="")
    about_me = models.CharField(max_length=100, null=True, blank=True)
    last_login = models.DateTimeField(_("last login"), null=True, blank=True)
    email = models.EmailField(_("email address"), unique=True)
    profile_image = models.CharField(max_length=250, null=True, blank=True)
    otp = models.IntegerField(null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    designation = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True, unique=True)
    is_active = models.BooleanField(default=False)
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=25)
    user_type = models.CharField(max_length=30, choices=Role.choices)
    is_org_staff = models.BooleanField(
        default=False,
        help_text="True for staff users created by an organization admin. "
        "Staff never receive an automatic monthly token allowance.",
    )
    email_verified = models.BooleanField(default=False)
    password_last_changed = models.DateTimeField(null=True, blank=True)
    keep_me_logged_in = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(
        default=False, help_text="User accepted Terms & Conditions"
    )
    referral_code = models.CharField(max_length=50, null=True, blank=True)
    full_name = models.CharField(max_length=201, null=True, blank=True, db_index=True)
    country = models.ForeignKey(
        "country.Country", on_delete=models.SET_NULL, null=True, blank=True
    )
    states = models.ForeignKey(
        "state.State", on_delete=models.SET_NULL, null=True, blank=True
    )
    city = models.ForeignKey(
        "city.City", on_delete=models.SET_NULL, null=True, blank=True
    )
    address = models.CharField(max_length=500, null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_created",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_updated",
    )
    updated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users_deleted",
    )
    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "user"
        ordering = ["-id"]

    def save(self, *args, **kwargs):
        skip_group_assignment = kwargs.pop("skip_group_assignment", False)
        user = kwargs.pop("user", None)
        update_fields = kwargs.get("update_fields")

        if self._state.adding:
            if user and not self.created_by_id:
                self.created_by = user
            self.updated_by = None
            self.updated_at = None
        else:
            if update_fields is None:
                if user:
                    self.updated_by = user
                if not self.deleted:
                    self.updated_at = timezone.now()
            else:
                if "updated_by" in update_fields and user:
                    self.updated_by = user
                if "updated_at" in update_fields and not self.deleted:
                    self.updated_at = timezone.now()

        self.full_name = f"{self.first_name} {self.last_name}".strip()
        super().save(*args, **kwargs)

        # Org staff are identity-only: never auto-assign a default role group;
        # the org owner assigns roles later via /assign-role/.
        if not skip_group_assignment and not self.is_org_staff:
            self.assign_group_based_on_role()

    def assign_group_based_on_role(self):
        # Soft-deleted users must never receive (or re-gain) a default role.
        if self.deleted:
            return

        role_group_mapping = {
            self.Role.STUDENT: "Student",
            self.Role.PARENT: "Parent",
            self.Role.PROFESSIONAL: "Professional",
            self.Role.SCHOOL_COLLEGE: "School College",
            self.Role.INSTITUTE: "Institute",
            self.Role.CORPORATE: "Corporate",
            self.Role.SUPER_ADMIN: "Super Admin",
        }

        group_name = role_group_mapping.get(self.user_type)
        if group_name:
            group = CustomGroup.objects.filter(name=group_name, deleted=False).first()
            if group and not self.groups.exists():
                self.groups.add(group)

    def get_owner_user(self):
        """Return the owning user account for this user.

        Organization staff act on behalf of the user that created them.
        """
        if self.is_org_staff and self.created_by:
            return self.created_by
        return self

    @property
    def full_name_property(self):
        return f"{self.first_name} {self.last_name}".strip()

    @cached_property
    def company(self):
        """Company this user belongs to.

        ``user.company`` was a direct FK before the model refactor removed it.
        This restores the attribute using the surviving relationships:
        first via the user's company-scoped groups (``CustomGroup.company``),
        falling back to the company the user created.
        """
        group = (
            self.groups.filter(customgroup__company__isnull=False)
            .select_related("customgroup__company")
            .first()
        )
        if group:
            company = group.customgroup.company
            if company:
                return company
        return Company.objects.filter(created_by=self).first()

    @property
    def subscription_info(self):
        from subscription.models import UserSubscription

        us = (
            UserSubscription.objects.filter(user=self, is_active=True, deleted=False)
            .select_related("plan_price__plan")
            .first()
        )
        if not us or not us.plan_price or not us.plan_price.plan:
            return None
        return {
            "package_name": us.plan_price.plan.package_name,
            "is_active": us.is_active,
            "end_date": us.end_date,
        }

    def upload_profile_image(self, profile_image_file):
        allowed_types = [".jpg", ".jpeg", ".png"]

        file_extension = os.path.splitext(profile_image_file.name)[1].lower()
        if file_extension not in allowed_types:
            raise ValueError(
                f"Invalid file type: {file_extension}. Allowed types are {', '.join(allowed_types)}."
            )

        current_value = getattr(self, "profile_image", None)

        try:
            if current_value:
                delete_uploaded_file(current_value)

            aws_file_url, presigned_url = upload_file_to_bucket(
                profile_image_file,
                allowed_types,
                "ProfileImage/",
                self.id,
                None,
            )
            self.profile_image = aws_file_url
            self.save(update_fields=["profile_image"])
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Failed to upload profile image: {str(e)}")


class AuthGroupModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)

    class Meta:
        db_table = "auth_group"
        managed = False


class ContentTypeModel(models.Model):
    id = models.AutoField(primary_key=True)
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        db_table = "django_content_type"
        managed = False


class AuthPermissionModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentTypeModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "auth_permission"
        managed = False


class AuthGroupPermissionsModel(models.Model):
    id = models.AutoField(primary_key=True)
    group = models.ForeignKey(AuthGroupModel, on_delete=models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermissionModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "auth_group_permissions"
        managed = False


class UserGroupsModel(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(AuthGroupModel, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = "user_groups"
        managed = False


class RoleFamily(models.Model):
    family_name = models.CharField(max_length=100)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="role_family_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="role_family_updated",
    )
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.id} - {self.family_name}"

    class Meta:
        db_table = "role_family"


class CustomGroup(Group):
    sequence = models.PositiveIntegerField()
    group_name = models.CharField(max_length=150, null=True)
    role_family = models.ForeignKey(
        RoleFamily, on_delete=models.SET_NULL, null=True, related_name="role_family"
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        related_name="company_group",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="group_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="group_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.sequence is None:
            last_record = (
                CustomGroup.objects.filter(created_by=self.created_by)
                .order_by("-sequence")
                .first()
            )
            self.sequence = (last_record.sequence + 1) if last_record else 1
        super(CustomGroup, self).save(*args, **kwargs)


class EmailPhoneVerify(models.Model):
    email = models.EmailField(max_length=150, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_otp = models.IntegerField(null=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_number_otp = models.IntegerField(null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="email_phone_verify_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="email_phone_verify_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    deleted = models.BooleanField(default=False)

    def __str__(self):
        if self.email:
            return f"{self.email} - {self.email_verified}"
        return f"{self.phone_number} - {self.phone_verified}"

    class Meta:
        db_table = "email_phone_verify"
