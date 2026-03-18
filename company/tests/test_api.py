import json
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from company.api.views import CompanyV1ViewSet
from company.models import Company
from company.views import CompanyViewSet
from user.models import User


class CompanyApiV1Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create(
            email="api-user@example.com",
            first_name="API",
            is_active=True,
        )

    @patch("company.api.views.CompanyOnboardingService.execute")
    def test_create_returns_standardized_success(self, mock_execute):
        company = Company.objects.create(
            name="API Co",
            email="api-co@example.com",
            phone="6666666666",
        )
        mock_execute.return_value = company

        payload = {
            "name": "API Co",
            "email": "api-co-new@example.com",
            "phone": "6666666667",
        }
        request = self.factory.post("/api/v1/company/", payload, format="json")
        force_authenticate(request, user=self.user)
        response = CompanyV1ViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Company created successfully")
        self.assertIn("data", response.data)

    @patch("company.api.views.CompanyUpdateService.execute")
    def test_update_uses_service_layer(self, mock_execute):
        company = Company.objects.create(
            name="API Co 2",
            email="api-co2@example.com",
            phone="6111111111",
        )
        company.first_name = "Updated Name"
        mock_execute.return_value = company

        request = self.factory.patch(
            f"/api/v1/company/{company.id}/",
            {"first_name": "Updated Name"},
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = CompanyV1ViewSet.as_view({"patch": "update"})(request, pk=company.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Company updated successfully")


class CompanyLegacyApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create(
            email="legacy-user@example.com",
            first_name="Legacy",
            is_active=True,
        )

    @patch("company.views.CompanyViewSet._create_welcome_subscription")
    @patch("company.views.CompanyOnboardingService.execute")
    def test_legacy_create_supports_form_data(self, mock_execute, mock_welcome):
        company = Company.objects.create(
            name="Legacy Co",
            email="legacy-co@example.com",
            phone="5555555555",
        )
        mock_execute.return_value = company
        mock_welcome.return_value = None

        form_payload = {
            "name": "Legacy Co",
            "email": "legacy-co-2@example.com",
            "phone": "5555555556",
        }
        request = self.factory.post(
            "/company/",
            {"form_data": json.dumps(form_payload)},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        response = CompanyViewSet.as_view({"post": "create"})(request)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Company created successfully")

    @patch("company.views.CompanyUpdateService.execute")
    def test_legacy_update_supports_form_data(self, mock_execute):
        company = Company.objects.create(
            name="Legacy Co 2",
            email="legacy2@example.com",
            phone="5444444444",
        )
        company.first_name = "New"
        mock_execute.return_value = company

        request = self.factory.patch(
            f"/company/{company.id}/",
            {"form_data": json.dumps({"first_name": "New"})},
            format="multipart",
        )
        force_authenticate(request, user=self.user)
        response = CompanyViewSet.as_view({"patch": "update"})(request, pk=company.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
