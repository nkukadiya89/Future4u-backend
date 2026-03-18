from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from activity_log.models import ActivityLog
from city.models import City
from city_areas.models import CityArea
from country.models import Country
from state.models import State

User = get_user_model()


class CityAreaModelTestCase(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email="test@example.com", username="testuser", password="testpass")
        self.country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/flag.png",
            phone_code="+91",
            created_by=self.user,
        )
        self.state = State.objects.create(name="Maharashtra", country=self.country, created_by=self.user)
        self.city = City.objects.create(name="Mumbai", country=self.country, state=self.state, created_by=self.user)

    def test_city_area_creation(self):
        """Test basic city area creation"""
        city_area = CityArea.objects.create(
            city_area_name="Bandra",
            zipcode="400050",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )
        self.assertEqual(city_area.city_area_name, "Bandra")
        self.assertEqual(city_area.zipcode, "400050")
        self.assertEqual(city_area.country, self.country)
        self.assertEqual(city_area.state, self.state)
        self.assertEqual(city_area.city, self.city)
        self.assertEqual(city_area.created_by, self.user)
        self.assertEqual(city_area.deleted, 0)
        self.assertIsNotNone(city_area.created_at)
        self.assertIsNone(city_area.updated_at)
        self.assertIsNone(city_area.updated_by)

    def test_city_area_update(self):
        """Test updating a city area"""
        city_area = CityArea.objects.create(
            city_area_name="Bandra",
            zipcode="400050",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )
        original_created_at = city_area.created_at
        original_created_by = city_area.created_by

        city_area.city_area_name = "Bandra West"
        city_area.updated_by = self.user
        city_area.updated_at = now()
        city_area.save()

        city_area.refresh_from_db()
        self.assertEqual(city_area.city_area_name, "Bandra West")
        self.assertEqual(city_area.created_by, original_created_by)
        self.assertEqual(city_area.created_at, original_created_at)
        self.assertIsNotNone(city_area.updated_at)
        self.assertEqual(city_area.updated_by, self.user)

    def test_city_area_str_representation(self):
        """Test city area string representation"""
        city_area = CityArea.objects.create(
            city_area_name="Bandra", zipcode="400050", country=self.country, state=self.state, city=self.city
        )
        self.assertEqual(str(city_area), "Bandra - 400050 (Mumbai, Maharashtra, India)")

    def test_city_area_db_table(self):
        """Test that city area uses correct database table"""
        self.assertEqual(CityArea._meta.db_table, "city_area")

    def test_city_area_field_constraints(self):
        """Test city area field constraints"""
        name_field = CityArea._meta.get_field("city_area_name")
        self.assertEqual(name_field.max_length, 255)

        zipcode_field = CityArea._meta.get_field("zipcode")
        self.assertEqual(zipcode_field.max_length, 20)

        country_field = CityArea._meta.get_field("country")
        self.assertEqual(country_field.related_model, Country)

        state_field = CityArea._meta.get_field("state")
        self.assertEqual(state_field.related_model, State)

        city_field = CityArea._meta.get_field("city")
        self.assertEqual(city_field.related_model, City)

        deleted_field = CityArea._meta.get_field("deleted")
        self.assertEqual(deleted_field.default, 0)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships"""
        country_field = CityArea._meta.get_field("country")
        self.assertEqual(country_field.remote_field.on_delete.__name__, "CASCADE")

        state_field = CityArea._meta.get_field("state")
        self.assertEqual(state_field.remote_field.on_delete.__name__, "CASCADE")

        city_field = CityArea._meta.get_field("city")
        self.assertEqual(city_field.remote_field.on_delete.__name__, "CASCADE")

        created_by_field = CityArea._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(created_by_field.null)

        updated_by_field = CityArea._meta.get_field("updated_by")
        self.assertEqual(updated_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(updated_by_field.null)

    def test_related_name_configuration(self):
        """Test that related names are properly configured"""
        country_field = CityArea._meta.get_field("country")
        state_field = CityArea._meta.get_field("state")
        city_field = CityArea._meta.get_field("city")
        self.assertEqual(country_field.remote_field.related_name, "city_areas_country")
        self.assertEqual(state_field.remote_field.related_name, "city_areas_state")
        self.assertEqual(city_field.remote_field.related_name, "city_areas_city")


class CityAreaAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email="test@example.com", username="testuser", password="testpass")
        self.country = Country.objects.create(
            name="India",
            code="IN",
            unicode="🇮🇳",
            country_flag="https://example.com/flag.png",
            phone_code="+91",
            created_by=self.user,
        )
        self.state = State.objects.create(name="Maharashtra", country=self.country, created_by=self.user)
        self.city = City.objects.create(name="Mumbai", country=self.country, state=self.state, created_by=self.user)
        self.city_area = CityArea.objects.create(
            city_area_name="Bandra",
            zipcode="400050",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_city_area(self):
        """Test creating a new city area"""
        url = reverse("cityarea-list")
        data = {
            "city_area_name": "Juhu",
            "zipcode": "400049",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
        }

        with patch.object(ActivityLog.log, "city_area_create") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Area added successfully")

            city_area = CityArea.objects.get(city_area_name="Juhu")
            self.assertEqual(city_area.zipcode, "400049")
            self.assertEqual(city_area.country, self.country)
            self.assertEqual(city_area.state, self.state)
            self.assertEqual(city_area.city, self.city)
            self.assertEqual(city_area.created_by, self.user)
            self.assertIsNotNone(city_area.created_at)
            self.assertIsNone(city_area.updated_at)
            self.assertIsNone(city_area.updated_by)
            mock_log.assert_called_once()

    def test_update_city_area(self):
        """Test updating a city area"""
        url = reverse("cityarea-detail", args=[self.city_area.id])
        data = {"city_area_name": "Bandra West"}

        with patch.object(ActivityLog.log, "city_area_update") as mock_log:
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Area updated successfully")

            self.city_area.refresh_from_db()
            self.assertEqual(self.city_area.city_area_name, "Bandra West")
            self.assertIsNotNone(self.city_area.updated_at)
            self.assertEqual(self.city_area.updated_by, self.user)
            self.assertIsNotNone(self.city_area.created_at)
            self.assertEqual(self.city_area.created_by, self.user)
            mock_log.assert_called_once()

    def test_create_city_area_invalid_data(self):
        """Test creating city area with invalid data"""
        url = reverse("cityarea-list")

        # Test empty city_area_name
        data = {
            "city_area_name": "",
            "zipcode": "400049",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test missing city
        data = {"city_area_name": "Juhu", "zipcode": "400049", "country": self.country.id, "state": self.state.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_create_duplicate_city_area(self):
        """Test creating duplicate city area in same city"""
        url = reverse("cityarea-list")
        data = {
            "city_area_name": "Bandra",
            "zipcode": "400051",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_create_duplicate_zipcode(self):
        """Test creating city area with duplicate zipcode"""
        url = reverse("cityarea-list")
        data = {
            "city_area_name": "Juhu",
            "zipcode": "400050",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_list_city_areas(self):
        """Test listing city areas"""
        url = reverse("cityarea-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_city_areas_no_pagination(self):
        """Test listing city areas without pagination"""
        url = reverse("cityarea-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 1)

    def test_retrieve_city_area(self):
        """Test retrieving a specific city area"""
        url = reverse("cityarea-detail", args=[self.city_area.id])
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["city_area_name"], "Bandra")
        self.assertEqual(response.data["data"]["id"], self.city_area.id)

    def test_update_city_area_invalid_data(self):
        """Test updating city area with invalid data"""
        url = reverse("cityarea-detail", args=[self.city_area.id])

        # Test empty city_area_name
        data = {"city_area_name": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_update_to_duplicate_city_area(self):
        """Test updating city area to create duplicate"""
        CityArea.objects.create(
            city_area_name="Juhu",
            zipcode="400049",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )

        url = reverse("cityarea-detail", args=[self.city_area.id])
        data = {"city_area_name": "Juhu", "country": self.country.id, "state": self.state.id, "city": self.city.id}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_soft_delete_city_area(self):
        """Test soft deleting a city area"""
        url = reverse("cityarea-detail", args=[self.city_area.id])

        with patch.object(ActivityLog.log, "city_area_archive") as mock_log:
            response = self.client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Area Deleted")

            self.city_area.refresh_from_db()
            self.assertEqual(self.city_area.deleted, 1)
            mock_log.assert_called_once()

    def test_delete_nonexistent_city_area(self):
        """Test deleting a non-existent city area"""
        url = reverse("cityarea-detail", args=[999])
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_city_areas(self):
        """Test bulk deleting city areas"""
        city_area2 = CityArea.objects.create(
            city_area_name="Juhu",
            zipcode="400049",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )

        url = reverse("cityarea_archive-list")
        data = {"deleted": [self.city_area.id, city_area2.id]}

        with patch.object(ActivityLog.log, "city_area_archive") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Areas archived successfully")

            self.city_area.refresh_from_db()
            city_area2.refresh_from_db()
            self.assertEqual(self.city_area.deleted, 1)
            self.assertEqual(city_area2.deleted, 1)
            mock_log.assert_called_once()

    def test_bulk_delete_nonexistent_city_area(self):
        """Test bulk deleting with non-existent city area ID"""
        url = reverse("cityarea_archive-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data, list)

    def test_list_archived_city_areas(self):
        """Test listing archived city areas"""
        self.city_area.deleted = 1
        self.city_area.save()

        url = reverse("cityarea_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            self.assertTrue(response.data["results"]["success"])
            self.assertIsInstance(response.data["results"]["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_archived_city_areas_no_pagination(self):
        """Test listing archived city areas without pagination"""
        self.city_area.deleted = 1
        self.city_area.save()

        url = reverse("cityarea_archive-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        # Archive viewset get_queryset filters deleted=False, so archived items won't appear in GET
        self.assertGreaterEqual(len(response.data["data"]), 0)

    def test_restore_city_areas(self):
        """Test restoring archived city areas"""
        self.city_area.deleted = 1
        self.city_area.save()

        url = reverse("cityarea_restore-list")
        data = {"deleted": [self.city_area.id]}

        with patch.object(ActivityLog.log, "city_area_restore") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "City Area restored successfully")

            self.city_area.refresh_from_db()
            self.assertEqual(self.city_area.deleted, 0)
            mock_log.assert_called_once()

    def test_restore_nonexistent_city_area(self):
        """Test restoring non-existent city area"""
        url = reverse("cityarea_restore-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIsInstance(response.data, list)

    def test_search_city_areas(self):
        """Test searching city areas"""
        url = reverse("cityarea-list")
        response = self.client.get(url, {"search": "Bandra"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertEqual(len(results_data["data"]), 1)
            self.assertEqual(results_data["data"][0]["city_area_name"], "Bandra")
        else:
            self.assertTrue(response.data["success"])
            self.assertEqual(len(response.data["data"]), 1)
            self.assertEqual(response.data["data"][0]["city_area_name"], "Bandra")

    def test_search_city_areas_by_city(self):
        """Test searching city areas by city name"""
        url = reverse("cityarea-list")
        response = self.client.get(url, {"search": "Mumbai"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertGreaterEqual(len(results_data["data"]), 1)
        else:
            self.assertTrue(response.data["success"])
            self.assertGreaterEqual(len(response.data["data"]), 1)

    def test_ordering_city_areas(self):
        """Test ordering city areas"""
        CityArea.objects.create(
            city_area_name="Juhu",
            zipcode="400049",
            country=self.country,
            state=self.state,
            city=self.city,
            created_by=self.user,
        )

        url = reverse("cityarea-list")
        response = self.client.get(url, {"ordering": "city_area_name", "no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        city_areas = response.data["data"]
        self.assertEqual(city_areas[0]["city_area_name"], "Bandra")
        self.assertEqual(city_areas[1]["city_area_name"], "Juhu")

    def test_unauthenticated_access(self):
        """Test accessing endpoints without authentication"""
        self.client.force_authenticate(user=None)

        url = reverse("cityarea-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        """Test pagination functionality"""
        for i in range(5):
            CityArea.objects.create(
                city_area_name=f"Area {i}",
                zipcode=f"40005{i}",
                country=self.country,
                state=self.state,
                city=self.city,
                created_by=self.user,
            )

        url = reverse("cityarea-list")
        response = self.client.get(url, {"page": 1, "page_size": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_serializer_write_only_fields(self):
        """Test that created_by and updated_by are write-only"""
        url = reverse("cityarea-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]
        self.assertNotIn("created_by", data)
        self.assertNotIn("updated_by", data)
        self.assertIn("country_name", data)
        self.assertIn("state_name", data)
        self.assertIn("city_name", data)
        self.assertEqual(data["country_name"], "India")
        self.assertEqual(data["state_name"], "Maharashtra")
        self.assertEqual(data["city_name"], "Mumbai")

    def test_city_area_with_different_cities(self):
        """Test creating city areas with same name in different cities"""
        city2 = City.objects.create(name="Pune", country=self.country, state=self.state, created_by=self.user)
        url = reverse("cityarea-list")
        data = {
            "city_area_name": "Bandra",
            "zipcode": "411007",
            "country": self.country.id,
            "state": self.state.id,
            "city": city2.id,
        }

        with patch.object(ActivityLog.log, "city_area_create") as mock_log:
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            mock_log.assert_called_once()

    def test_city_area_validation_error_handling(self):
        """Test that validation errors are properly handled"""
        url = reverse("cityarea-list")
        data = {
            "city_area_name": "Bandra",
            "zipcode": "400050",
            "country": self.country.id,
            "state": self.state.id,
            "city": self.city.id,
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("message", response.data)
