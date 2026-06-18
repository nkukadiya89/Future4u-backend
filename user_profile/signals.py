from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from user_profile.models import (
    CorporateProfile,
    InstituteProfile,
    ParentProfile,
    ProfessionalProfile,
    SchoolCollegeProfile,
    StudentProfile,
    UserProfile,
)

User = get_user_model()


def _create_organization_profile(profile_model, user):
    profile_model.objects.get_or_create(
        user=user,
        defaults={"created_by": user},
    )


@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        # Create UserProfile ONLY for Super Admin
        if instance.user_type == User.Role.SUPER_ADMIN:
            transaction.on_commit(
                lambda: UserProfile.objects.get_or_create(user=instance)
            )

        # Create role-specific profile based on user_type
        elif instance.user_type == User.Role.STUDENT:
            transaction.on_commit(
                lambda: StudentProfile.objects.get_or_create(user=instance)
            )

        elif instance.user_type == User.Role.PROFESSIONAL:
            transaction.on_commit(
                lambda: ProfessionalProfile.objects.get_or_create(user=instance)
            )

        elif instance.user_type == User.Role.PARENT:
            transaction.on_commit(
                lambda: ParentProfile.objects.get_or_create(user=instance)
            )

        elif instance.user_type == User.Role.INSTITUTE:
            transaction.on_commit(
                lambda user=instance: _create_organization_profile(InstituteProfile, user)
            )

        elif instance.user_type == User.Role.SCHOOL_COLLEGE:
            transaction.on_commit(
                lambda user=instance: _create_organization_profile(
                    SchoolCollegeProfile, user
                )
            )

        elif instance.user_type == User.Role.CORPORATE:
            transaction.on_commit(
                lambda user=instance: _create_organization_profile(CorporateProfile, user)
            )
