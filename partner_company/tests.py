import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from city.models import City
from city_areas.models import CityArea
from country.models import Country
from partner_company.models import PartnerCompany, PartnerCompanyDocument
from partner_company.serializers import (
    PartnerCompanyArchiveSerializer,
    PartnerCompanyDocumentArchiveSerializer,
    PartnerCompanyDocumentSerializer,
    PartnerCompanySerializer,
)
from state.models import State
from user.models import CustomGroup

User = get_user_model()


class BaseTestCase(APITestCase):
    """Base test case with common setup"""

    def setUp(self):
        self.client = APIClient()

        # Create test location data
        self.country = Country.objects.create(
            name="India", code="IN", unicode="India", country_flag="https://example.com/flag.png", phone_code="91"
        )
        self.state = State.objects.create(name="Gujarat", country=self.country)
        self.city = City.objects.create(name="Ahmedabad", state=self.state, country=self.country)
        self.city_area = CityArea.objects.create(
            city_area_name="Bopal", city=self.city, state=self.state, country=self.country, zipcode="380058"
        )

        # Create required groups
        self.company_admin_group = CustomGroup.objects.create(
            name="Company Admin", sequence=1, group_name="Company Admin"
        )
        self.partner_company_admin_group = CustomGroup.objects.create(
            name="Partner Company Admin", sequence=2, group_name="Partner Company Admin"
        )

        # Create test users
        self.admin_user = User.objects.create_user(
            email="admin@example.com", password="testpass123", first_name="Admin", is_staff=True, is_active=True
        )

        self.partner_user = User.objects.create_user(
            email="partner@example.com", password="testpass123", first_name="Partner User", is_active=True
        )

        # Create test partner company
        self.partner_company = PartnerCompany.objects.create(
            company_name="Test Company",
            person_name="Test Person",
            email="company@example.com",
            phone="1234567890",
            gst_address_country="India",
            gst_address_state="Gujarat",
            gst_address_city="Ahmedabad",
            gst_no="22AAAAA0000A1Z5",
            status="active",
            created_by=self.admin_user,
        )

        # Associate partner user with partner company
        self.partner_user.partner_company = self.partner_company
        self.partner_user.save()

        # Create another partner company for testing isolation
        self.other_partner_company = PartnerCompany.objects.create(
            company_name="Other Company",
            person_name="Other Person",
            email="other@example.com",
            phone="0987654321",
            gst_address_country="India",
            gst_address_state="Gujarat",
            gst_address_city="Ahmedabad",
            status="active",
            created_by=self.admin_user,
        )

        # Create test documents
        self.document1 = PartnerCompanyDocument.objects.create(
            partner_company=self.partner_company, document_title="Test Document 1", created_by=self.partner_user
        )

        self.document2 = PartnerCompanyDocument.objects.create(
            partner_company=self.partner_company, document_title="Test Document 2", created_by=self.partner_user
        )

        self.other_document = PartnerCompanyDocument.objects.create(
            partner_company=self.other_partner_company,
            document_title="Other Company Document",
            created_by=self.admin_user,
        )

    def get_tokens_for_user(self, user):
        """Generate JWT tokens for user"""
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

    def authenticate_user(self, user):
        """Authenticate a user for API calls"""
        tokens = self.get_tokens_for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')

    def create_test_image(self):
        """Create a test image file for upload testing"""
        file_obj = BytesIO()
        image = Image.new("RGB", (100, 100), "red")
        image.save(file_obj, "JPEG")
        file_obj.seek(0)
        return InMemoryUploadedFile(file_obj, None, "test_image.jpg", "image/jpeg", len(file_obj.getvalue()), None)

    def create_test_pdf(self):
        """Create a test PDF file for upload testing"""
        pdf_content = b"%PDF-1.4 test content"
        return SimpleUploadedFile("test_document.pdf", pdf_content, content_type="application/pdf")


class PartnerCompanyModelTest(BaseTestCase):
    """Test cases for PartnerCompany model"""

    def test_partner_company_creation(self):
        """Test creating a partner company"""
        company = PartnerCompany.objects.create(
            company_name="New Company",
            person_name="New Person",
            email="new@example.com",
            phone="5555555555",
            status="pending",
        )

        self.assertEqual(company.company_name, "New Company")
        self.assertEqual(company.status, "pending")
        self.assertEqual(company.deleted, 0)
        self.assertFalse(company.is_active)

    def test_partner_company_str_method(self):
        """Test string representation of PartnerCompany"""
        self.assertEqual(str(self.partner_company), "Test Company")

    def test_partner_company_status_choices(self):
        """Test status choices validation"""
        valid_statuses = ["pending", "active", "inactive"]
        for company_status in valid_statuses:
            self.partner_company.status = company_status
            self.partner_company.save()
            self.assertEqual(self.partner_company.status, company_status)


class PartnerCompanyDocumentModelTest(BaseTestCase):
    """Test cases for PartnerCompanyDocument model"""

    def test_document_creation(self):
        """Test creating a partner company document"""
        document = PartnerCompanyDocument.objects.create(
            partner_company=self.partner_company, document_title="New Document", created_by=self.partner_user
        )

        self.assertEqual(document.partner_company, self.partner_company)
        self.assertEqual(document.document_title, "New Document")
        self.assertEqual(document.deleted, 0)

    def test_document_str_method(self):
        """Test string representation of PartnerCompanyDocument"""
        expected = f"{self.document1.id} - {self.document1.document_title}"
        self.assertEqual(str(self.document1), expected)


class PartnerCompanyViewSetTest(BaseTestCase):
    """Test cases for PartnerCompany ViewSet"""

    def test_list_partner_companies_authenticated(self):
        """Test listing partner companies with authentication"""
        self.authenticate_user(self.admin_user)
        url = reverse("partner_company-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("data", response.data["results"])

    def test_list_partner_companies_unauthenticated(self):
        """Test listing partner companies without authentication"""
        url = reverse("partner_company-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "partner_company.serializers.create_partner_company_role_family",
        return_value={"success": True, "partner_company_group": []},
    )
    @patch("utils.aws_file_upload.upload_file_to_bucket")
    def test_create_partner_company(self, mock_upload, mock_role_family):
        """Test creating a new partner company"""
        self.authenticate_user(self.admin_user)

        # Mock the file upload function
        mock_upload.return_value = ("http://example.com/logo.jpg", "http://presigned.url")

        form_data = {
            "company_name": "New Test Company",
            "person_name": "New Person",
            "email": "newcompany@example.com",
            "phone": 9999999999,
            "gst_address_country": "India",
            "gst_address_state": "Gujarat",
            "gst_address_city": "Ahmedabad",
            "gst_no": "22BBBBB0000B1Z5",
        }

        url = reverse("partner_company-list")
        data = {"form_data": json.dumps(form_data), "partner_company_logo": self.create_test_image()}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PartnerCompany.objects.filter(company_name="New Test Company").exists())

    def test_retrieve_partner_company(self):
        """Test retrieving a specific partner company"""
        self.authenticate_user(self.admin_user)
        url = reverse("partner_company-detail", kwargs={"pk": self.partner_company.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["company_name"], "Test Company")

    def test_update_partner_company(self):
        """Test updating a partner company"""
        self.authenticate_user(self.admin_user)

        form_data = {
            "company_name": "Updated Company",
            "person_name": "Updated Person",
            "email": self.partner_company.email,
            "phone": self.partner_company.phone,
        }

        url = reverse("partner_company-detail", kwargs={"pk": self.partner_company.id})
        data = {"form_data": json.dumps(form_data)}

        response = self.client.put(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.partner_company.refresh_from_db()
        self.assertEqual(self.partner_company.company_name, "Updated Company")

    def test_soft_delete_partner_company(self):
        """Test soft deleting a partner company"""
        self.authenticate_user(self.admin_user)
        url = reverse("partner_company-detail", kwargs={"pk": self.partner_company.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.partner_company.refresh_from_db()
        self.assertEqual(self.partner_company.deleted, 1)


class PartnerCompanyDocumentViewSetTest(BaseTestCase):
    """Test cases for PartnerCompanyDocument ViewSet"""

    def test_list_documents_partner_user(self):
        """Test listing documents as partner user - should only see own company docs"""
        self.authenticate_user(self.partner_user)
        url = reverse("partner_company_document-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]["data"]), 2)  # Only own company's documents

    def test_list_documents_with_partner_company_id(self):
        """Test listing documents with partner_company_id parameter"""
        self.authenticate_user(self.admin_user)
        url = f"{reverse('partner_company_document-list')}?partner_company_id={self.partner_company.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]["data"]), 2)  # Specific company's documents

    def test_create_document_partner_user(self):
        """Test creating document as partner user"""
        self.authenticate_user(self.partner_user)

        form_data = {"document_title": "New Document"}

        url = reverse("partner_company_document-list")
        data = {"form_data": json.dumps(form_data), "document_file": self.create_test_pdf()}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PartnerCompanyDocument.objects.filter(
                document_title="New Document", partner_company=self.partner_company
            ).exists()
        )

    def test_create_document_with_partner_company_id(self):
        """Test creating document for specific partner company"""
        self.authenticate_user(self.admin_user)

        form_data = {"document_title": "Admin Created Document"}

        url = f"{reverse('partner_company_document-list')}?partner_company_id={self.partner_company.id}"
        data = {"form_data": json.dumps(form_data), "document_file": self.create_test_pdf()}

        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            PartnerCompanyDocument.objects.filter(
                document_title="Admin Created Document", partner_company=self.partner_company
            ).exists()
        )

    def test_update_document(self):
        """Test updating a document"""
        self.authenticate_user(self.partner_user)

        form_data = {"document_title": "Updated Document"}

        url = reverse("partner_company_document-detail", kwargs={"pk": self.document1.id})
        data = {"form_data": json.dumps(form_data)}

        response = self.client.put(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.document1.refresh_from_db()
        self.assertEqual(self.document1.document_title, "Updated Document")

    def test_delete_document(self):
        """Test soft deleting a document"""
        self.authenticate_user(self.partner_user)
        url = reverse("partner_company_document-detail", kwargs={"pk": self.document1.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.document1.refresh_from_db()
        self.assertEqual(self.document1.deleted, 1)

    def test_document_access_isolation(self):
        """Test that partner user cannot access other company's documents"""
        self.authenticate_user(self.partner_user)
        url = reverse("partner_company_document-detail", kwargs={"pk": self.other_document.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PartnerCompanyArchiveRestoreTest(BaseTestCase):
    """Test cases for Partner Company Archive and Restore functionality"""

    def test_archive_partner_companies(self):
        """Test archiving multiple partner companies"""
        self.authenticate_user(self.admin_user)

        url = reverse("partner_company_archive-list")
        data = {"deleted": [self.partner_company.id, self.other_partner_company.id]}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.partner_company.refresh_from_db()
        self.other_partner_company.refresh_from_db()
        self.assertEqual(self.partner_company.deleted, 1)
        self.assertEqual(self.other_partner_company.deleted, 1)

    def test_restore_partner_companies(self):
        """Test restoring archived partner companies"""
        self.authenticate_user(self.admin_user)

        # First archive them
        self.partner_company.deleted = 1
        self.partner_company.save()

        url = reverse("partner_company_restore-list")
        data = {"deleted": [self.partner_company.id]}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.partner_company.refresh_from_db()
        self.assertEqual(self.partner_company.deleted, 0)


class PartnerCompanyDocumentArchiveRestoreTest(BaseTestCase):
    """Test cases for Partner Company Document Archive and Restore functionality"""

    def test_archive_documents(self):
        """Test archiving multiple documents"""
        self.authenticate_user(self.partner_user)

        url = reverse("partner_company_document_archive-list")
        data = {"deleted": [self.document1.id, self.document2.id]}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.document1.refresh_from_db()
        self.document2.refresh_from_db()
        self.assertEqual(self.document1.deleted, 1)
        self.assertEqual(self.document2.deleted, 1)

    def test_restore_documents(self):
        """Test restoring archived documents"""
        self.authenticate_user(self.partner_user)

        # First archive them
        self.document1.deleted = 1
        self.document1.save()

        url = reverse("partner_company_document_restore-list")
        data = {"deleted": [self.document1.id]}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.document1.refresh_from_db()
        self.assertEqual(self.document1.deleted, 0)

    def test_archive_documents_with_partner_company_id(self):
        """Test archiving documents with specific partner company context"""
        self.authenticate_user(self.admin_user)

        url = f"{reverse('partner_company_document_archive-list')}?partner_company_id={self.partner_company.id}"
        data = {"deleted": [self.document1.id]}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.document1.refresh_from_db()
        self.assertEqual(self.document1.deleted, 1)


class PartnerCompanySerializerTest(BaseTestCase):
    """Test cases for Partner Company Serializers"""

    def test_partner_company_serializer_validation(self):
        """Test validation in PartnerCompanySerializer"""
        data = {
            "company_name": "Test Company",  # Duplicate name
            "email": "company@example.com",  # Duplicate email
            "phone": "1234567890",  # Duplicate phone
            "person_name": "Test Person",
        }

        serializer = PartnerCompanySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # Check that validation failed due to duplicate data
        error_str = str(serializer.errors)
        self.assertTrue(
            "already exists" in error_str or "company_name" in error_str or "email" in error_str or "phone" in error_str
        )

    def test_partner_company_document_serializer(self):
        """Test PartnerCompanyDocumentSerializer"""
        data = {"partner_company": self.partner_company.id, "document_title": "Test Document"}

        serializer = PartnerCompanyDocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_partner_company_delete_serializer(self):
        """Test PartnerCompanyArchiveSerializer"""
        data = {"deleted": [self.partner_company.id]}

        serializer = PartnerCompanyArchiveSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_document_delete_serializer_with_context(self):
        """Test PartnerCompanyDocumentArchiveSerializer with request context"""
        # Create a mock request object
        mock_request = MagicMock()
        mock_request.query_params = {"partner_company_id": str(self.partner_company.id)}
        mock_request.user = self.partner_user

        data = {"deleted": [self.document1.id]}

        serializer = PartnerCompanyDocumentArchiveSerializer(data=data, context={"request": mock_request})
        self.assertTrue(serializer.is_valid())


class PartnerCompanyPermissionTest(BaseTestCase):
    """Test cases for Partner Company Permissions and Access Control"""

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access any endpoints"""
        endpoints = [
            reverse("partner_company-list"),
            reverse("partner_company_document-list"),
            reverse("partner_company_archive-list"),
            reverse("partner_company_restore-list"),
            reverse("partner_company_document_archive-list"),
            reverse("partner_company_document_restore-list"),
        ]

        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_partner_user_document_isolation(self):
        """Test that partner users can only see their own company's documents"""
        self.authenticate_user(self.partner_user)

        # Should see own documents
        url = reverse("partner_company_document-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should only contain documents from own company
        for doc in response.data["results"]["data"]:
            document = PartnerCompanyDocument.objects.get(id=doc["id"])
            self.assertEqual(document.partner_company, self.partner_company)


class PartnerCompanyIntegrationTest(BaseTestCase):
    """Integration tests for complete workflows"""

    @patch(
        "partner_company.serializers.create_partner_company_role_family",
        return_value={"success": True, "partner_company_group": []},
    )
    def test_complete_partner_company_workflow(self, mock_role_family):
        """Test complete partner company creation and document management workflow"""
        self.authenticate_user(self.admin_user)

        # 1. Create partner company
        form_data = {
            "company_name": "Integration Test Company",
            "person_name": "Integration Person",
            "email": "integration@example.com",
            "phone": 8888888888,
            "gst_address_country": "India",
            "gst_address_state": "Gujarat",
            "gst_address_city": "Ahmedabad",
            "gst_no": "22CCCCC0000C1Z5",
        }

        url = reverse("partner_company-list")
        data = {"form_data": json.dumps(form_data)}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_company = PartnerCompany.objects.get(company_name="Integration Test Company")

        # 2. Create document for the company
        doc_form_data = {"document_title": "Integration Document"}

        url = f"{reverse('partner_company_document-list')}?partner_company_id={new_company.id}"
        data = {"form_data": json.dumps(doc_form_data), "document_file": self.create_test_pdf()}
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 3. Verify document is associated with correct company
        document = PartnerCompanyDocument.objects.get(document_title="Integration Document")
        self.assertEqual(document.partner_company, new_company)

        # 4. Archive and restore workflow
        url = f"{reverse('partner_company_document_archive-list')}?partner_company_id={new_company.id}"
        data = {"deleted": [document.id]}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.deleted, 1)

        # 5. Restore document
        url = f"{reverse('partner_company_document_restore-list')}?partner_company_id={new_company.id}"
        data = {"deleted": [document.id]}
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        document.refresh_from_db()
        self.assertEqual(document.deleted, 0)
