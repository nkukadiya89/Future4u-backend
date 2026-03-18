import logging

from django.utils.crypto import get_random_string

from company.repositories.company_repository import CompanyRepository
from company.tasks import send_company_reset_password_email_task
from user.models import CustomGroup

logger = logging.getLogger(__name__)


class CompanyOnboardingService:
    def __init__(self, repository=None):
        self.repository = repository or CompanyRepository()

    def execute(self, validated_data: dict, actor=None):
        password = validated_data.pop("password", None) or get_random_string(12)

        user_data = {
            "email": validated_data["email"],
            "first_name": validated_data.get("first_name") or "",
            "phone": validated_data.get("phone"),
            "designation": validated_data.get("designation"),
            "status": "pending",
            "is_active": False,
        }
        company_data = {
            **validated_data,
            "status": "pending",
            "is_active": False,
        }

        company, user = self.repository.create_company_with_admin(
            company_data=company_data,
            user_data=user_data,
            password=password,
            actor=actor,
        )

        # Assign default group when available.
        company_admin_group = CustomGroup.objects.filter(name="Company Admin").first()
        if company_admin_group is not None:
            company_admin_group.user_set.add(user)

        # Async side effect (email) with safe fallback.
        try:
            send_company_reset_password_email_task.delay(user.id)
        except Exception:
            logger.exception(
                "Failed to queue reset password email task; falling back to sync send",
                extra={"user_id": user.id},
            )
            send_company_reset_password_email_task(user.id)

        return company
