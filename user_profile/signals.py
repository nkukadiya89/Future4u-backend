from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from user_profile.models import (
    ParentProfile,
    ProfessionalProfile,
    StudentProfile,
    UserProfile,
)

User = get_user_model()


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
