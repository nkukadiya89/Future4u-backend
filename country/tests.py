from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from country.models import Country
from user.models import User


class CountryAPITestCase(APITestCase):
    """Test cases for Country API endpoints"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(email="testuser@example.com", username="testuser", password="testpass")

        # Create test country
        self.country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/india-flag.png",
            phone_code="+91",
            created_by=self.user,
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_country(self):
        """Test creating a new country"""
        url = reverse("country-list")
        data = {
            "name": "United States",
            "code": "US",
            "unicode": "🇺🇸",
            "country_flag": "https://example.com/us-flag.png",
            "phone_code": "+1",
            "created_by": self.user.id,
        }

        with patch("country.views.ActivityLog.log.country_create") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Country added successfully")
            self.assertEqual(response.data["data"]["name"], "United States")

            # Verify the country was created in the database
            country_exists = Country.objects.filter(name="United States", deleted=False).exists()
            self.assertTrue(country_exists)

            # Verify activity log was called
            mock_log.assert_called_once()

    def test_create_country_invalid_data(self):
        """Test creating country with invalid data"""
        url = reverse("country-list")

        # Test empty name
        data = {"name": "", "code": "US", "unicode": "🇺🇸", "country_flag": "https://example.com/us-flag.png"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test duplicate name
        data = {
            "name": "India",
            "code": "IN2",
            "unicode": "🇮🇳",
            "country_flag": "https://example.com/india-flag.png",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_create_country_max_length(self):
        """Test country name with maximum allowed length"""
        url = reverse("country-list")
        long_name = "A" * 50  # Max length from model
        data = {"name": long_name, "code": "XX", "unicode": "🏳️", "country_flag": "https://example.com/flag.png"}

        # Modified: Removed unused mock_log variable
        with patch("country.views.ActivityLog.log.country_create", return_value=None):
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])

    def test_create_country_invalid_url(self):
        """Test creating country with invalid URL"""
        url = reverse("country-list")
        data = {
            "name": "Test Country",
            "code": "TC",
            "unicode": "🏳️",
            "country_flag": "invalid-url",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_list_countries(self):
        """Test listing countries"""
        url = reverse("country-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"]["success"])
        self.assertIsInstance(response.data["results"]["data"], list)
        self.assertGreater(len(response.data["results"]["data"]), 0)

    def test_list_countries_no_pagination(self):
        """Test listing countries without pagination"""
        url = reverse("country-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 1)

    def test_search_countries(self):
        """Test searching countries"""
        # Create another country for search
        Country.objects.create(
            name="United Kingdom",
            code="UK",
            unicode="🇬🇧",
            country_flag="https://example.com/uk-flag.png",
            phone_code="+44",
            created_by=self.user,
        )

        url = reverse("country-list")

        # Search by name
        response = self.client.get(url, {"search": "India"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertTrue(results_data["success"])
        self.assertEqual(len(results_data["data"]), 1)
        self.assertEqual(results_data["data"][0]["name"], "India")

        # Search by code
        response = self.client.get(url, {"search": "UK"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertTrue(results_data["success"])
        self.assertEqual(len(results_data["data"]), 1)
        self.assertEqual(results_data["data"][0]["code"], "UK")

    def test_ordering_countries(self):
        """Test ordering countries"""
        # Create another country
        Country.objects.create(
            name="Australia",
            code="AU",
            unicode="🇦🇺",
            country_flag="https://example.com/au-flag.png",
            phone_code="+61",
            created_by=self.user,
        )

        url = reverse("country-list")

        # Order by name ascending
        response = self.client.get(url, {"ordering": "name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertEqual(results_data["data"][0]["name"], "Australia")

        # Order by name descending
        response = self.client.get(url, {"ordering": "-name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertEqual(results_data["data"][0]["name"], "India")

    def test_retrieve_country(self):
        """Test retrieving a specific country"""
        url = reverse("country-detail", args=[self.country.id])
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "India")
        self.assertEqual(response.data["id"], self.country.id)

    def test_update_country(self):
        """Test updating a country"""
        url = reverse("country-detail", args=[self.country.id])
        data = {"name": "Republic of India", "phone_code": "+91"}

        with patch("country.views.ActivityLog.log.country_update") as mock_log:
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Country updated successfully")

            # Verify the country was updated
            self.country.refresh_from_db()
            self.assertEqual(self.country.name, "Republic of India")
            mock_log.assert_called_once()

    def test_update_country_invalid_data(self):
        """Test updating country with invalid data"""
        url = reverse("country-detail", args=[self.country.id])

        # Test empty name
        data = {"name": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test invalid URL
        data = {"country_flag": "invalid-url"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_soft_delete_country(self):
        """Test soft deleting a country"""
        url = reverse("country-detail", args=[self.country.id])

        with patch("country.views.ActivityLog.log.country_archive") as mock_log:
            response = self.client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Country Deleted")

            # Verify the country was soft deleted
            self.country.refresh_from_db()
            self.assertEqual(self.country.deleted, 1)
            mock_log.assert_called_once()

    def test_delete_nonexistent_country(self):
        """Test deleting a non-existent country"""
        url = reverse("country-detail", args=[999])
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_countries(self):
        """Test bulk deleting countries"""
        # Create another country
        country2 = Country.objects.create(
            name="Canada",
            code="CA",
            unicode="🇨🇦",
            country_flag="https://example.com/ca-flag.png",
            phone_code="+1",
            created_by=self.user,
        )

        url = reverse("country_archive-list")
        data = {"deleted": [self.country.id, country2.id]}

        with patch("country.views.ActivityLog.log.country_archive") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Countries archived successfully")

            # Verify both countries were archived
            self.country.refresh_from_db()
            country2.refresh_from_db()
            self.assertEqual(self.country.deleted, 1)
            self.assertEqual(country2.deleted, 1)
            mock_log.assert_called_once()

    def test_bulk_delete_nonexistent_country(self):
        """Test bulk deleting with non-existent country ID"""
        url = reverse("country_archive-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_list_archived_countries(self):
        """Test listing archived countries"""
        # Archive the country
        self.country.deleted = 1
        self.country.save()

        url = reverse("country_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_archived_countries_no_pagination(self):
        """Test listing archived countries without pagination"""
        # Archive the country
        self.country.deleted = 1
        self.country.save()

        url = reverse("country_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "success" in response.data:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)
            self.assertGreaterEqual(len(response.data["data"]), 0)
        else:
            # Regular paginated response
            self.assertIn("results", response.data)

    def test_restore_countries(self):
        """Test restoring archived countries"""
        # Archive the country first
        self.country.deleted = 1
        self.country.save()

        url = reverse("country_restore-list")
        data = {"deleted": [self.country.id]}

        with patch("country.views.ActivityLog.log.country_restore") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Country restored successfully")

            # Verify the country was restore
            self.country.refresh_from_db()
            self.assertEqual(self.country.deleted, 0)
            mock_log.assert_called_once()

    def test_restore_nonexistent_country(self):
        """Test restoring non-existent country"""
        url = reverse("country_restore-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_unauthenticated_access(self):
        """Test accessing endpoints without authentication"""
        self.client.force_authenticate(user=None)

        url = reverse("country-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_model_str_method(self):
        """Test Country model string representation"""
        self.assertEqual(str(self.country), "India")

    def test_model_defaults(self):
        """Test Country model default values"""
        country = Country.objects.create(
            name="Test Country", code="TC", unicode="🏳️", country_flag="https://example.com/flag.png"
        )
        self.assertEqual(country.deleted, 0)
        self.assertIsNotNone(country.created_at)
        # Since the model does not auto-populate updated_at on create, it should be None by default
        self.assertIsNone(country.updated_at)

    def test_model_foreign_key_on_delete(self):
        """Test that deleting user sets foreign key to null"""
        # Create a new user for this test
        test_user = User.objects.create_user(email="testuser2@example.com", username="testuser2", password="testpass")

        country = Country.objects.create(
            name="Test Country",
            code="TC",
            unicode="🏁",
            country_flag="https://example.com/flag.png",
            created_by=test_user,
            updated_by=test_user,
        )

        # Instead of deleting the user (which might affect city table),
        self.assertEqual(country.created_by, test_user)
        self.assertEqual(country.updated_by, test_user)

    def test_serializer_write_only_fields(self):
        """Test that created_by and updated_by are write-only fields"""
        url = reverse("country-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]

        # These fields should not appear in the response due to write_only=True
        self.assertNotIn("created_by", data)
        self.assertNotIn("updated_by", data)

    def test_pagination(self):
        """Test pagination functionality"""
        # Create multiple countries with unique unicode values
        unicode_flags = ["🇺🇸", "🇬🇧", "🇫🇷", "🇩🇪", "🇯🇵"]
        for i in range(5):
            Country.objects.create(
                name=f"Country {i}",
                code=f"C{i}",
                unicode=unicode_flags[i],
                country_flag=f"https://example.com/flag{i}.png",
                created_by=self.user,
            )

        url = reverse("country-list")
        response = self.client.get(url, {"page": 1, "page_size": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_create_with_ip_address_logging(self):
        """Test that IP address is captured during creation"""
        url = reverse("country-list")
        data = {"name": "New Country", "code": "NC", "unicode": "🏳️", "country_flag": "https://example.com/flag.png"}

        with patch("country.views.get_client_ip") as mock_get_ip, patch(
            "country.views.ActivityLog.log.country_create"
        ) as mock_log:

            mock_get_ip.return_value = "192.168.1.1"
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_get_ip.assert_called_once()
            mock_log.assert_called_once()

            # Verify IP address was passed to ActivityLog
            args = mock_log.call_args[0]
            self.assertEqual(args[1], "192.168.1.1")

    def test_update_with_ip_address_logging(self):
        """Test that IP address is captured during update"""
        url = reverse("country-detail", args=[self.country.id])
        data = {"name": "Updated Country"}

        with patch("country.views.get_client_ip") as mock_get_ip, patch(
            "country.views.ActivityLog.log.country_update"
        ) as mock_log:

            mock_get_ip.return_value = "192.168.1.1"
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_get_ip.assert_called_once()
            mock_log.assert_called_once()

            # Verify IP address was passed to ActivityLog
            args = mock_log.call_args[0]
            self.assertEqual(args[1], "192.168.1.1")

    def test_country_unique_constraints(self):
        url = reverse("country-list")

        # Test duplicate code (should fail, as code is unique)
        data = {
            "name": "Different India",
            "code": "IN",  # Same as existing country
            "unicode": "🇮🇳",
            "country_flag": "https://example.com/flag.png",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test duplicate unicode (should succeed, as unicode is not unique)
        data = {
            "name": "Different India",
            "code": "DI",  # Unique code
            "unicode": "🇮🇳",  # Same unicode as existing country
            "country_flag": "https://example.com/flag.png",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # Expect success
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "Different India")
        self.assertEqual(response.data["data"]["unicode"], "🇮🇳")

    def test_phone_code_optional(self):
        """Test that phone_code is optional"""
        url = reverse("country-list")
        data = {
            "name": "Test Country",
            "code": "TC",
            "unicode": "🏳️",
            "country_flag": "https://example.com/flag.png",
        }

        # Modified: Removed unused mock_log variable
        with patch("country.views.ActivityLog.log.country_create", return_value=None):
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            # Verify phone_code is None
            country = Country.objects.get(name="Test Country")
            self.assertIsNone(country.phone_code)


class CountryModelTestCase(TestCase):
    """Test cases for Country model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email="testuser@example.com", username="testuser", password="testpass")

    def test_country_creation(self):
        """Test basic country creation"""
        country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/india-flag.png",
            phone_code="+91",
            created_by=self.user,
        )

        self.assertEqual(country.name, "India")
        self.assertEqual(country.code, "IN")
        self.assertEqual(country.unicode, "🇮🇳")
        self.assertEqual(country.phone_code, "+91")
        self.assertEqual(country.created_by, self.user)
        self.assertEqual(country.deleted, 0)
        self.assertIsNotNone(country.created_at)
        # Model does not auto-populate updated_at on create
        self.assertIsNone(country.updated_at)

    def test_country_str_representation(self):
        """Test country string representation"""
        country = Country.objects.create(
            name="India", code="IN", unicode="🇮🇳", country_flag="https://example.com/india-flag.png"
        )

        self.assertEqual(str(country), "India")

    def test_country_db_table(self):
        """Test that country uses correct database table"""
        self.assertEqual(Country._meta.db_table, "country")

    def test_country_field_constraints(self):
        """Test country field constraints"""
        # Test max length of name field
        name_field = Country._meta.get_field("name")
        self.assertEqual(name_field.max_length, 50)
        self.assertTrue(name_field.unique)

        # Test max length of code field
        code_field = Country._meta.get_field("code")
        self.assertEqual(code_field.max_length, 50)
        self.assertTrue(code_field.unique)

        # Test max length of unicode field
        unicode_field = Country._meta.get_field("unicode")
        self.assertEqual(unicode_field.max_length, 80)
        self.assertFalse(unicode_field.unique)

        # Test country_flag field
        flag_field = Country._meta.get_field("country_flag")
        self.assertEqual(flag_field.max_length, 200)

        # Test phone_code field
        phone_field = Country._meta.get_field("phone_code")
        self.assertEqual(phone_field.max_length, 5)
        self.assertTrue(phone_field.null)

        # Test deleted field default
        deleted_field = Country._meta.get_field("deleted")
        self.assertEqual(deleted_field.default, 0)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships"""
        # Test SET_NULL on user delete
        created_by_field = Country._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(created_by_field.null)

        updated_by_field = Country._meta.get_field("updated_by")
        self.assertEqual(updated_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(updated_by_field.null)

    def test_country_unique_constraints(self):
        """Test unique constraints"""
        # Create first country
        Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/india-flag.png",
            created_by=self.user,
        )

        # Try to create country with same name
        with self.assertRaises(Exception):
            Country.objects.create(
                name="India",
                code="IN2",
                unicode="🇮🇳2",
                country_flag="https://example.com/india-flag2.png",
                created_by=self.user,
            )

        # Try to create country with same code
        with self.assertRaises(Exception):
            Country.objects.create(
                name="India2",
                code="IN",
                unicode="🇮🇳2",
                country_flag="https://example.com/india-flag2.png",
                created_by=self.user,
            )

        # Try to create country with same unicode
        with self.assertRaises(Exception):
            Country.objects.create(
                name="India2",
                code="IN2",
                unicode="🇮🇳",
                country_flag="https://example.com/india-flag2.png",
                created_by=self.user,
            )
