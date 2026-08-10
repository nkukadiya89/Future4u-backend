import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from city.models import City
from country.models import Country
from employee.models import Employee
from employee.serializers import (
    AddEmployeeSerializer,
    EmployeeArchiveSerializer,
    EmployeeRestoreSerializer,
)
from state.models import State

User = get_user_model()


class EmployeeModelTest(TestCase):
    """Test cases for Employee model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="testpass123",
            first_name="Creator",
            last_name="User",
        )
        self.country = Country.objects.create(name="India")
        self.state = State.objects.create(name="Karnataka", country=self.country)
        self.city = City.objects.create(
            name="Bangalore", state=self.state, country=self.country
        )

    def test_create_employee(self):
        """Test creating an Employee"""
        employee = Employee.objects.create(
            email="test@example.com",
            phone="9876543210",
            first_name="Test",
            last_name="Employee",
            created_by=self.user,
            permanent_address_country=self.country,
            permanent_address_state=self.state,
            permanent_address_city=self.city,
        )
        self.assertEqual(employee.email, "test@example.com")
        self.assertEqual(employee.phone, "9876543210")
        self.assertEqual(employee.first_name, "Test")
        self.assertEqual(employee.last_name, "Employee")
        self.assertEqual(employee.status, "pending")
        self.assertEqual(employee.created_by, self.user)
        self.assertEqual(employee.permanent_address_country, self.country)
        self.assertIsNotNone(employee.created_at)
        self.assertIsNotNone(employee.updated_at)
        self.assertEqual(employee.deleted, 0)

    def test_employee_str_method(self):
        """Test string representation of Employee"""
        employee = Employee.objects.create(
            email="test@example.com",
            phone="9876543210",
            first_name="Test",
            last_name="Employee",
            created_by=self.user,
        )
        self.assertEqual(str(employee), "Test")

    def test_employee_default_values(self):
        """Test default values for Employee"""
        employee = Employee.objects.create(
            email="test@example.com", phone="9876543210", first_name="Test"
        )
        self.assertEqual(employee.status, "pending")
        self.assertEqual(employee.deleted, 0)
        self.assertIsNone(employee.created_by)
        self.assertIsNone(employee.updated_by)
        self.assertIsNotNone(employee.updated_at)
        self.assertIsNone(employee.deleted_by)
        self.assertIsNone(employee.deleted_at)

    def test_employee_soft_delete(self):
        """Test soft delete functionality"""
        employee = Employee.objects.create(
            email="test@example.com",
            phone="9876543210",
            first_name="Test",
            created_by=self.user,
        )
        employee.deleted = 1
        employee.deleted_by = self.user
        employee.deleted_at = now()
        employee.save()
        self.assertTrue(Employee.objects.filter(id=employee.id).exists())
        self.assertEqual(employee.deleted, 1)
        self.assertEqual(employee.deleted_by, self.user)
        self.assertIsNotNone(employee.deleted_at)

    def test_employee_profile_photo_upload(self):
        """Test profile photo upload"""
        employee = Employee.objects.create(
            email="test@example.com",
            phone="9876543210",
            first_name="Test",
            created_by=self.user,
        )
        employee.profile_photo = "old_photo.jpg"
        employee.save()
        with patch("employee.models.upload_file_to_bucket") as mock_upload, patch(
            "employee.models.delete_uploaded_file"
        ) as mock_delete:
            mock_upload.return_value = ("path/to/photo.jpg", "presigned_url")
            employee.upload_profile_photo_presentation(MagicMock(name="photo.jpg"))
            self.assertEqual(employee.profile_photo, "path/to/photo.jpg")
            mock_upload.assert_called_once()
            mock_delete.assert_called_once_with("old_photo.jpg")


class EmployeeSerializerTest(TestCase):
    """Test cases for Employee serializers"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="testpass123",
            first_name="Creator",
            last_name="User",
        )
        self.country = Country.objects.create(name="India")
        self.state = State.objects.create(name="Karnataka", country=self.country)
        self.city = City.objects.create(
            name="Bangalore", state=self.state, country=self.country
        )
        self.employee = Employee.objects.create(
            email="test@example.com",
            phone="9876543210",
            first_name="Test",
            created_by=self.user,
        )
        self.test_user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            phone="9876543210",
        )
        self.employee_data = {
            "email": "test@example.com",
            "phone": 9876543210,
            "first_name": "Test",
            "last_name": "Employee",
            "created_by": self.user,
            "permanent_address_country": self.country,
            "permanent_address_state": self.state,
            "permanent_address_city": self.city,
        }

    def test_add_employee_serializer_create(self):
        """Test creating Employee through serializer"""
        serializer_data = {
            "email": "newemployee@example.com",
            "phone": 9876543211,
            "first_name": "New",
            "last_name": "Employee",
            "password": "testpass123",
            "permission": [],
            "role": [],
            "permanent_address_country": self.country.id,
            "permanent_address_state": self.state.id,
            "permanent_address_city": self.city.id,
        }
        with patch("employee.serializers.get_client_ip") as mock_get_ip, patch(
            "employee.serializers.ActivityLog"
        ) as mock_activity_log, patch(
            "django.contrib.auth.models.Group"
        ) as mock_group:
            mock_get_ip.return_value = "127.0.0.1"
            mock_activity_log.log.employee_create = MagicMock()
            mock_group.objects.get.return_value = MagicMock()
            request_mock = MagicMock(user=self.user)
            serializer = AddEmployeeSerializer(
                data=serializer_data, context={"request": request_mock}
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            employee = serializer.save()
            self.assertEqual(employee.email, "newemployee@example.com")
            self.assertEqual(employee.phone, "9876543211")
            self.assertEqual(employee.created_by, self.user)
            user = User.objects.get(email="newemployee@example.com")
            self.assertEqual(user.email, employee.email)
            mock_activity_log.log.employee_create.assert_called_once()

    def test_add_employee_serializer_validation(self):
        """Test serializer validation"""
        serializer_data = {
            "email": "test@example.com",
            "phone": 9876543211,
            "first_name": "Another",
            "password": "testpass123",
            "permission": [],
            "role": [],
        }
        serializer = AddEmployeeSerializer(
            data=serializer_data, context={"request": MagicMock(user=self.user)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

        serializer_data = {
            "email": "new@example.com",
            "phone": 123,
            "first_name": "Test",
            "password": "testpass123",
            "permission": [],
            "role": [],
        }
        serializer = AddEmployeeSerializer(
            data=serializer_data, context={"request": MagicMock(user=self.user)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_employee_archive_serializer(self):
        """Test EmployeeArchiveSerializer"""
        employee1 = Employee.objects.create(
            email="test1@example.com",
            phone="9876543210",
            first_name="Test1",
            created_by=self.user,
        )
        employee2 = Employee.objects.create(
            email="test2@example.com",
            phone="9876543211",
            first_name="Test2",
            created_by=self.user,
        )
        delete_data = {"deleted": [employee1.id, employee2.id]}
        with patch("employee.serializers.ActivityLog") as mock_activity_log:
            mock_activity_log.log.employee_archive = MagicMock()
            serializer = EmployeeArchiveSerializer(
                data=delete_data, context={"request": MagicMock(user=self.user)}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()
            employee1.refresh_from_db()
            employee2.refresh_from_db()
            self.assertEqual(employee1.deleted, 1)
            self.assertEqual(employee2.deleted, 1)
            self.assertEqual(employee1.status, "pending")
            self.assertEqual(employee2.status, "pending")

    def test_employee_restore_serializer(self):
        """Test EmployeeRestoreSerializer"""
        employee1 = Employee.objects.create(
            email="test1@example.com",
            phone="9876543210",
            first_name="Test1",
            created_by=self.user,
            deleted=True,
        )
        employee2 = Employee.objects.create(
            email="test2@example.com",
            phone="9876543211",
            first_name="Test2",
            created_by=self.user,
            deleted=True,
        )
        restore_data = {"deleted": [employee1.id, employee2.id]}
        with patch("employee.serializers.ActivityLog") as mock_activity_log:
            mock_activity_log.log.employee_restore = MagicMock()
            serializer = EmployeeRestoreSerializer(
                data=restore_data, context={"request": MagicMock(user=self.user)}
            )
            self.assertTrue(serializer.is_valid())
            serializer.save()
            employee1.refresh_from_db()
            employee2.refresh_from_db()
            self.assertEqual(employee1.deleted, False)
            self.assertEqual(employee2.deleted, 0)
            self.assertEqual(employee1.status, "pending")
            self.assertEqual(employee2.status, "pending")


class BaseAPITestCase(APITestCase):
    """Base test case with common setup for API tests"""

    def setUp(self):
        """Set up test data and authentication"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="creator@example.com",
            password="testpass123",
            first_name="Creator",
            last_name="User",
        )
        self.user.is_active = True
        self.user.save()
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        self.country = Country.objects.create(name="India")
        self.state = State.objects.create(name="Karnataka", country=self.country)
        self.city = City.objects.create(
            name="Bangalore", state=self.state, country=self.country
        )
        self.employee1 = Employee.objects.create(
            email="test1@example.com",
            phone="9876543210",
            first_name="Test1",
            last_name="Employee1",
            created_by=self.user,
        )
        self.employee2 = Employee.objects.create(
            email="test2@example.com",
            phone="9876543211",
            first_name="Test2",
            last_name="Employee2",
            created_by=self.user,
        )
        self.archived_employee = Employee.objects.create(
            email="archived@example.com",
            phone="9876543212",
            first_name="Archived",
            last_name="Employee",
            created_by=self.user,
            deleted=True,
            status="inactive",
        )
        self.user1 = User.objects.create_user(
            email=self.employee1.email,
            password="oldpass123",
            phone="9876543210",
        )
        self.user2 = User.objects.create_user(
            email=self.employee2.email,
            password="oldpass123",
            phone="9876543211",
        )


class AddEmployeeViewSetTest(BaseAPITestCase):
    """Test cases for AddEmployeeViewSet"""

    def setUp(self):
        super().setUp()
        self.list_url = reverse("employee-list")
        self.detail_url = lambda pk: reverse("employee-detail", args=[pk])

    def test_list_employees_authenticated(self):
        """Test listing employees with authentication"""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("success", response.data["results"])
        self.assertTrue(response.data["results"]["success"])
        self.assertIn("data", response.data["results"])
        self.assertIsInstance(response.data["results"]["data"], list)
        self.assertEqual(len(response.data["results"]["data"]), 2)

    def test_list_employees_unauthenticated(self):
        """Test listing employees without authentication"""
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_with_no_pagination(self):
        """Test listing with no_pagination parameter"""
        response = self.client.get(self.list_url, {"no_pagination": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 2)

    def test_search_employees(self):
        """Test searching employees"""
        response = self.client.get(self.list_url, {"search": "Test1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("success", response.data["results"])
        self.assertTrue(response.data["results"]["success"])
        self.assertIn("data", response.data["results"])
        self.assertGreaterEqual(len(response.data["results"]["data"]), 1)
        found = any(
            "Test1" in result["first_name"]
            for result in response.data["results"]["data"]
        )
        self.assertTrue(found)

    def test_ordering_employees(self):
        """Test ordering employees"""
        response = self.client.get(self.list_url, {"ordering": "first_name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("success", response.data["results"])
        self.assertTrue(response.data["results"]["success"])
        self.assertIn("data", response.data["results"])
        results = response.data["results"]["data"]
        names = [result["first_name"] for result in results]
        self.assertEqual(names, sorted(names))

    @patch("employee.models.upload_file_to_bucket")
    @patch("employee.serializers.get_client_ip")
    @patch("employee.serializers.ActivityLog")
    def test_create_employee(self, mock_activity_log, mock_get_ip, mock_upload_file):
        """Test creating a new employee"""
        mock_get_ip.return_value = "127.0.0.1"
        mock_upload_file.return_value = ("path/to/photo.jpg", "presigned_url")
        mock_activity_log.log.employee_create = MagicMock()
        data = {
            "form_data": json.dumps(
                {
                    "email": "new@example.com",
                    "phone": 9876543213,
                    "first_name": "New",
                    "last_name": "Employee",
                    "password": "testpass123",
                    "permission": [],
                    "role": [],
                    "permanent_address_country": self.country.id,
                    "permanent_address_state": self.state.id,
                    "permanent_address_city": self.city.id,
                }
            ),
            "profile_photo": MagicMock(name="photo.jpg"),
        }
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["message"],
            "Employee created. Temporary password sent to their email.",
        )
        employee = Employee.objects.get(email="new@example.com")
        self.assertEqual(employee.phone, "9876543213")
        self.assertEqual(employee.profile_photo, "path/to/photo.jpg")
        user = User.objects.get(email="new@example.com")
        self.assertEqual(user.email, employee.email)
        mock_activity_log.log.employee_create.assert_called_once()

    def test_create_employee_invalid_data(self):
        """Test creating employee with invalid data"""
        data = {
            "form_data": json.dumps(
                {
                    "email": "test1@example.com",
                    "phone": 9876543213,
                    "first_name": "New",
                    "password": "testpass123",
                }
            )
        }
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    @patch("employee.models.upload_file_to_bucket")
    @patch("employee.serializers.get_client_ip")
    @patch("employee.serializers.ActivityLog")
    def test_update_employee(self, mock_activity_log, mock_get_ip, mock_upload_file):
        """Test updating an employee"""
        mock_get_ip.return_value = "127.0.0.1"
        mock_upload_file.return_value = ("path/to/new_photo.jpg", "presigned_url")
        mock_activity_log.log.employee_modify = MagicMock()
        data = {
            "form_data": json.dumps(
                {
                    "email": "updated@example.com",
                    "phone": 9876543214,
                    "first_name": "Updated",
                    "last_name": "Employee",
                    "permanent_address_country": self.country.id,
                    "permanent_address_state": self.state.id,
                    "permanent_address_city": self.city.id,
                }
            ),
            "profile_photo": MagicMock(name="new_photo.jpg"),
        }
        response = self.client.put(
            self.detail_url(self.employee1.id), data, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.employee1.refresh_from_db()
        self.assertEqual(self.employee1.email, "updated@example.com")
        self.assertEqual(self.employee1.phone, "9876543214")
        self.assertEqual(self.employee1.profile_photo, "path/to/new_photo.jpg")
        user = User.objects.get(email=self.employee1.email)
        self.assertEqual(user.email, "updated@example.com")
        mock_activity_log.log.employee_modify.assert_called_once()

    @patch("employee.views.delete_uploaded_file")
    def test_profile_photo_delete(self, mock_delete_file):
        """Test deleting profile photo"""
        self.employee1.profile_photo = "path/to/photo.jpg"
        self.employee1.save()
        response = self.client.patch(
            self.detail_url(self.employee1.id) + "profile-photo-delete/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.employee1.refresh_from_db()
        self.assertIsNone(self.employee1.profile_photo)
        mock_delete_file.assert_called_once()

    def test_get_employee_basic_info(self):
        """Test getting employee basic info"""
        response = self.client.get(
            self.detail_url(self.employee1.id) + "employee-basic-info/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Test1")
        self.assertEqual(response.data["email"], "test1@example.com")

    def test_update_employee_details(self):
        """Test updating employee details"""
        data = {
            "form_data": json.dumps(
                {"first_name": "Updated", "last_name": "NewLast", "phone": 9876543214}
            )
        }
        response = self.client.patch(
            self.detail_url(self.employee1.id) + "update-employee-details/", data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee1.refresh_from_db()
        self.assertEqual(self.employee1.first_name, "Updated")
        self.assertEqual(self.employee1.last_name, "NewLast")
        self.assertEqual(self.employee1.phone, "9876543214")
        user = User.objects.get(email=self.employee1.email)
        self.assertEqual(user.first_name, "Updated")

    def test_change_employee_password(self):
        """Test changing employee password"""
        data = {
            "old_password": "oldpass123",
            "new_password": "newpass123",
            "re_enter_password": "newpass123",
        }
        response = self.client.patch(
            self.detail_url(self.employee1.id) + "change-employee-password/", data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertTrue(self.user1.check_password("newpass123"))


class EmployeeArchiveViewSetTest(BaseAPITestCase):
    """Test cases for EmployeeArchiveViewSet"""

    def setUp(self):
        super().setUp()
        self.archive_url = reverse("employee_archive-list")

    def test_list_archived_employees(self):
        """Test listing archived employees"""
        response = self.client.get(self.archive_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("success", response.data["results"])
        self.assertTrue(response.data["results"]["success"])
        self.assertIn("data", response.data["results"])
        self.assertGreaterEqual(len(response.data["results"]["data"]), 1)

    def test_list_archived_with_no_pagination(self):
        """Test listing archived employees with no pagination"""
        response = self.client.get(self.archive_url, {"no_pagination": "1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertGreaterEqual(len(response.data["data"]), 1)

    @patch("employee.views.ActivityLog")
    def test_bulk_archive_employees(self, mock_activity_log):
        """Test bulk archiving employees"""
        mock_activity_log.log.employee_archive = MagicMock()
        data = {"deleted": [self.employee1.id, self.employee2.id]}
        response = self.client.post(self.archive_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Users archived successfully")
        self.employee1.refresh_from_db()
        self.employee2.refresh_from_db()
        self.assertEqual(self.employee1.deleted, 1)
        self.assertEqual(self.employee2.deleted, 1)


class EmployeeRestoreViewSetTest(BaseAPITestCase):
    """Test cases for EmployeeRestoreViewSet"""

    def setUp(self):
        super().setUp()
        self.restore_url = reverse("employee_restore-list")

    @patch("employee.views.ActivityLog")
    def test_restore_employees(self, mock_activity_log):
        """Test restoring archived employees"""
        mock_activity_log.log.employee_restore = MagicMock()
        data = {"deleted": [self.archived_employee.id]}
        response = self.client.post(self.restore_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "User restored successfully")
        self.archived_employee.refresh_from_db()
        self.assertEqual(self.archived_employee.deleted, 0)
        self.assertEqual(self.archived_employee.status, "active")
        mock_activity_log.log.employee_restore.assert_called_once()
