from django.test import TestCase

from company.models import Company
from company.repositories.company_repository import CompanyRepository
from user.models import User


class CompanyRepositoryTests(TestCase):
    def test_create_company_with_admin_creates_linked_user_and_profile(self):
        actor = User.objects.create(
            email="actor@example.com",
            first_name="Actor",
            is_active=True,
        )
        repository = CompanyRepository()
        company_data = {
            "name": "Acme Pvt Ltd",
            "email": "acme@example.com",
            "phone": "9999999999",
        }
        user_data = {
            "email": "owner@example.com",
            "first_name": "Owner",
            "phone": "8888888888",
            "status": "pending",
            "is_active": False,
        }

        company, user = repository.create_company_with_admin(
            company_data=company_data,
            user_data=user_data,
            password="TempPass@123",
            actor=actor,
        )

        self.assertEqual(user.company_id, company.id)
        self.assertEqual(company.created_by_id, actor.id)
        self.assertEqual(company.company_percentage.count(), 1)

    def test_update_company_syncs_linked_users(self):
        actor = User.objects.create(
            email="actor2@example.com",
            first_name="Actor2",
            is_active=True,
        )
        company = Company.objects.create(
            name="Acme",
            email="acme-sync@example.com",
            phone="9000000000",
        )
        user = User.objects.create(
            email="linked@example.com",
            first_name="Before",
            phone="8111111111",
            company=company,
            is_active=True,
        )

        repository = CompanyRepository()
        updated_company = repository.update_company(
            company=company,
            update_data={
                "first_name": "After",
                "phone": "9222222222",
            },
            actor=actor,
        )
        user.refresh_from_db()

        self.assertEqual(updated_company.first_name, "After")
        self.assertEqual(updated_company.updated_by_id, actor.id)
        self.assertEqual(user.first_name, "After")
        self.assertEqual(user.phone, "9222222222")
