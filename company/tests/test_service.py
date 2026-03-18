from unittest.mock import Mock, patch

from django.test import TestCase

from company.services.company_update_service import CompanyUpdateService
from company.services.onboarding_service import CompanyOnboardingService


class CompanyServiceTests(TestCase):
    @patch("company.services.onboarding_service.CustomGroup")
    @patch("company.services.onboarding_service.send_company_reset_password_email_task")
    def test_onboarding_service_calls_repo_and_dispatches_task(
        self, mock_task, mock_group
    ):
        mock_repo = Mock()
        company = Mock()
        user = Mock(id=42)
        mock_repo.create_company_with_admin.return_value = (company, user)
        mock_group.objects.filter.return_value.first.return_value = None

        service = CompanyOnboardingService(repository=mock_repo)
        payload = {
            "name": "Service Co",
            "email": "service@example.com",
            "phone": "7777777777",
            "first_name": "Service",
            "designation": "Admin",
        }

        result = service.execute(payload, actor=None)

        self.assertEqual(result, company)
        mock_repo.create_company_with_admin.assert_called_once()
        mock_task.delay.assert_called_once_with(42)

    def test_update_service_delegates_to_repository(self):
        mock_repo = Mock()
        company = Mock()
        updated_company = Mock()
        mock_repo.update_company.return_value = updated_company

        service = CompanyUpdateService(repository=mock_repo)
        result = service.execute(company=company, validated_data={"name": "Updated"})

        self.assertEqual(result, updated_company)
        mock_repo.update_company.assert_called_once()
