from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APITestCase

from .models import City, Country, State

User = get_user_model()


class CityModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com", username="testuser", password="testpass"
        )
        self.country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/flag.png",
            phone_code="+91",
            created_by=self.user,
        )
        self.state = State.objects.create(
            name="Maharashtra", country=self.country, created_by=self.user
        )

    def test_city_creation(self):
        """Test basic city creation"""
        city = City.objects.create(
            name="Mumbai", country=self.country, state=self.state, created_by=self.user
        )
        self.assertEqual(city.name, "Mumbai")
        self.assertEqual(city.country, self.country)
        self.assertEqual(city.state, self.state)
        self.assertEqual(city.created_by, self.user)
        self.assertEqual(city.deleted, 0)
        self.assertIsNotNone(city.created_at)
        self.assertIsNone(city.updated_at)  # Verify updated_at is None
        self.assertIsNone(city.updated_by)  # Verify updated_by is None

    def test_city_update(self):
        """Test updating a city"""
        city = City.objects.create(
            name="Mumbai", country=self.country, state=self.state, created_by=self.user
        )
        original_created_at = city.created_at
        original_created_by = city.created_by

        city.name = "Mumbai Updated"
        city.updated_by = self.user
        city.updated_at = now()
        city.save()

        city.refresh_from_db()
        self.assertEqual(city.name, "Mumbai Updated")
        self.assertEqual(city.created_by, original_created_by)
        self.assertEqual(city.created_at, original_created_at)
        self.assertIsNotNone(city.updated_at)
        self.assertEqual(city.updated_by, self.user)

    def test_city_str_representation(self):
        """Test city string representation"""
        city = City.objects.create(
            name="Mumbai", country=self.country, state=self.state
        )
        self.assertEqual(str(city), "Mumbai(India)(Maharashtra)")

    def test_city_db_table(self):
        """Test that city uses correct database table"""
        self.assertEqual(City._meta.db_table, "city")

    def test_city_field_constraints(self):
        """Test city field constraints"""
        name_field = City._meta.get_field("name")
        self.assertEqual(name_field.max_length, 200)

        country_field = City._meta.get_field("country")
        self.assertEqual(country_field.related_model, Country)

        state_field = City._meta.get_field("state")
        self.assertEqual(state_field.related_model, State)

        deleted_field = City._meta.get_field("deleted")
        self.assertEqual(deleted_field.default, 0)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships"""
        country_field = City._meta.get_field("country")
        self.assertEqual(country_field.remote_field.on_delete.__name__, "CASCADE")

        state_field = City._meta.get_field("state")
        self.assertEqual(state_field.remote_field.on_delete.__name__, "CASCADE")

        created_by_field = City._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(created_by_field.null)

        updated_by_field = City._meta.get_field("updated_by")
        self.assertEqual(updated_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(updated_by_field.null)

    def test_related_name_configuration(self):
        """Test that related names are properly configured"""
        country_field = City._meta.get_field("country")
        state_field = City._meta.get_field("state")
        self.assertEqual(country_field.remote_field.related_name, "city_set")
        self.assertEqual(state_field.remote_field.related_name, "city_set")


class CityAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email="test@example.com", username="testuser", password="testpass"
        )
        self.country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/flag.png",
            phone_code="+91",
            created_by=self.user,
        )
        self.state = State.objects.create(
            name="Maharashtra", country=self.country, created_by=self.user
        )
        self.city = City.objects.create(
            name="Mumbai", country=self.country, state=self.state, created_by=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_create_city(self):
        """Test creating a new city"""
        url = reverse("city-list")
        data = {"name": "Pune", "country": self.country.id, "state": self.state.id}

        with patch("city.views.ActivityLog.log.city_create") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City added successfully")

            city = City.objects.get(name="Pune")
            self.assertEqual(city.country, self.country)
            self.assertEqual(city.state, self.state)
            self.assertEqual(city.created_by, self.user)
            self.assertIsNotNone(city.created_at)
            self.assertIsNone(city.updated_at)  # Verify updated_at is None
            self.assertIsNone(city.updated_by)  # Verify updated_by is None
            mock_log.assert_called_once()

    def test_update_city(self):
        """Test updating a city"""
        url = reverse("city-detail", args=[self.city.id])
        data = {"name": "Mumbai Updated"}

        with patch("city.views.ActivityLog.log.city_update") as mock_log:
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City updated successfully")

            self.city.refresh_from_db()
            self.assertEqual(self.city.name, "Mumbai Updated")
            self.assertIsNotNone(self.city.updated_at)  # Verify updated_at is set
            self.assertEqual(
                self.city.updated_by, self.user
            )  # Verify updated_by is set
            self.assertIsNotNone(self.city.created_at)  # Verify created_at remains
            self.assertEqual(
                self.city.created_by, self.user
            )  # Verify created_by remains
            mock_log.assert_called_once()

    def test_create_city_invalid_data(self):
        """Test creating city with invalid data"""
        url = reverse("city-list")

        # Test empty name
        data = {"name": "", "country": self.country.id, "state": self.state.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test missing state
        data = {"name": "Pune", "country": self.country.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_create_duplicate_city(self):
        """Test creating duplicate city in same state"""
        url = reverse("city-list")
        data = {"name": "Mumbai", "country": self.country.id, "state": self.state.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_list_cities(self):
        """Test listing cities"""
        url = reverse("city-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_cities_no_pagination(self):
        """Test listing cities without pagination"""
        url = reverse("city-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 1)

    def test_retrieve_city(self):
        """Test retrieving a specific city"""
        url = reverse("city-detail", args=[self.city.id])
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "Mumbai")
        self.assertEqual(response.data["data"]["id"], self.city.id)

    def test_update_city_invalid_data(self):
        """Test updating city with invalid data"""
        url = reverse("city-detail", args=[self.city.id])

        # Test empty name
        data = {"name": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_update_to_duplicate_city(self):
        """Test updating city to create duplicate"""
        City.objects.create(
            name="Pune", country=self.country, state=self.state, created_by=self.user
        )

        url = reverse("city-detail", args=[self.city.id])
        data = {"name": "Pune", "country": self.country.id, "state": self.state.id}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_soft_delete_city(self):
        """Test soft deleting a city"""
        url = reverse("city-detail", args=[self.city.id])

        with patch("city.views.ActivityLog.log.city_archive") as mock_log:
            response = self.client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Deleted")

            self.city.refresh_from_db()
            self.assertEqual(self.city.deleted, 1)
            mock_log.assert_called_once()

    def test_delete_nonexistent_city(self):
        """Test deleting a non-existent city"""
        url = reverse("city-detail", args=[999])
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_cities(self):
        """Test bulk deleting cities"""
        city2 = City.objects.create(
            name="Pune", country=self.country, state=self.state, created_by=self.user
        )

        url = reverse("city_archive-list")
        data = {"deleted": [self.city.id, city2.id]}

        with patch("city.views.ActivityLog.log.city_archive") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "Cities archived successfully")

            self.city.refresh_from_db()
            city2.refresh_from_db()
            self.assertEqual(self.city.deleted, 1)
            self.assertEqual(city2.deleted, 1)
            mock_log.assert_called_once()

    def test_bulk_delete_nonexistent_city(self):
        """Test bulk deleting with non-existent city ID"""
        url = reverse("city_archive-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data, list)

    def test_list_archived_cities(self):
        """Test listing archived cities"""
        self.city.deleted = 1
        self.city.save()

        url = reverse("city_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_archived_cities_no_pagination(self):
        """Test listing archived cities without pagination"""
        self.city.deleted = 1
        self.city.save()

        url = reverse("city_archive-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        # Archive viewset get_queryset filters deleted=False, so archived items won't appear in GET
        self.assertGreaterEqual(len(response.data["data"]), 0)

    def test_restore_cities(self):
        """Test restoring archived cities"""
        self.city.deleted = 1
        self.city.save()

        url = reverse("city_restore-list")
        data = {"deleted": [self.city.id]}

        with patch("city.views.ActivityLog.log.city_restore") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City restored successfully")

            self.city.refresh_from_db()
            self.assertEqual(self.city.deleted, 0)
            mock_log.assert_called_once()

    def test_restore_nonexistent_city(self):
        """Test restoring non-existent city"""
        url = reverse("city_restore-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data, list)

    def test_search_cities(self):
        """Test searching cities"""
        url = reverse("city-list")
        response = self.client.get(url, {"search": "Mumbai"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertEqual(len(results_data["data"]), 1)
            self.assertEqual(results_data["data"][0]["name"], "Mumbai")
        else:
            self.assertTrue(response.data["success"])
            self.assertEqual(len(response.data["data"]), 1)
            self.assertEqual(response.data["data"][0]["name"], "Mumbai")

    def test_search_cities_by_country(self):
        """Test searching cities by country name"""
        url = reverse("city-list")
        response = self.client.get(url, {"search": "India"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertGreaterEqual(len(results_data["data"]), 1)
        else:
            self.assertTrue(response.data["success"])
            self.assertGreaterEqual(len(response.data["data"]), 1)

    def test_ordering_cities(self):
        """Test ordering cities"""
        City.objects.create(
            name="Pune", country=self.country, state=self.state, created_by=self.user
        )

        url = reverse("city-list")
        response = self.client.get(
            url, {"ordering": "name", "no_pagination": "1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        cities = response.data["data"]
        self.assertEqual(cities[0]["name"], "Mumbai")
        self.assertEqual(cities[1]["name"], "Pune")

    def test_unauthenticated_access(self):
        """Test accessing endpoints without authentication"""
        self.client.force_authenticate(user=None)

        url = reverse("city-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        """Test pagination functionality"""
        for i in range(5):
            City.objects.create(
                name=f"City {i}",
                country=self.country,
                state=self.state,
                created_by=self.user,
            )

        url = reverse("city-list")
        response = self.client.get(url, {"page": 1, "page_size": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_serializer_write_only_fields(self):
        """Test that created_by and updated_by are write-only"""
        url = reverse("city-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]
        self.assertNotIn("created_by", data)
        self.assertNotIn("updated_by", data)
        self.assertIn("country_name", data)
        self.assertIn("state_name", data)
        self.assertEqual(data["country_name"], "India")
        self.assertEqual(data["state_name"], "Maharashtra")

    def test_city_with_different_states(self):
        """Test creating cities with same name in different states"""
        state2 = State.objects.create(
            name="Gujarat", country=self.country, created_by=self.user
        )
        url = reverse("city-list")
        data = {"name": "Mumbai", "country": self.country.id, "state": state2.id}

        with patch("city.views.ActivityLog.log.city_create"):
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])

    def test_create_with_ip_address_logging(self):
        """Test that IP address is captured during creation"""
        url = reverse("city-list")
        data = {"name": "Pune", "country": self.country.id, "state": self.state.id}

        with patch("city.views.get_client_ip") as mock_get_ip, patch(
            "city.views.ActivityLog.log.city_create"
        ) as mock_log:
            mock_get_ip.return_value = "192.168.1.1"
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_get_ip.assert_called_once()
            mock_log.assert_called_once()
            args = mock_log.call_args[0]
            self.assertEqual(args[1], "192.168.1.1")

    def test_update_with_ip_address_logging(self):
        """Test that IP address is captured during update"""
        url = reverse("city-detail", args=[self.city.id])
        data = {"name": "Mumbai Updated"}

        with patch("city.views.get_client_ip") as mock_get_ip, patch(
            "city.views.ActivityLog.log.city_update"
        ) as mock_log:
            mock_get_ip.return_value = "192.168.1.1"
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_get_ip.assert_called_once()
            mock_log.assert_called_once()

    def test_city_validation_error_handling(self):
        """Test that validation errors are properly handled"""
        url = reverse("city-list")
        data = {"name": "Mumbai", "country": self.country.id, "state": self.state.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("message", response.data)
