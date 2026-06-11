from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from country.models import Country
from state.models import State

User = get_user_model()


class StateModelTestCase(TestCase):

    def setUp(self):
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

    def test_state_creation(self):
        """Test basic state creation"""
        state = State.objects.create(
            name="Maharashtra", country=self.country, created_by=self.user
        )

        self.assertEqual(state.name, "Maharashtra")
        self.assertEqual(state.country, self.country)
        self.assertEqual(state.created_by, self.user)
        self.assertEqual(state.deleted, 0)
        self.assertIsNotNone(state.created_at)
        # Model has auto_now=True on updated_at, so it's set on create
        self.assertIsNotNone(state.updated_at)

    def test_state_str_representation(self):
        """Test state string representation"""
        state = State.objects.create(
            name="Maharashtra", country=self.country, created_by=self.user
        )

        self.assertEqual(str(state), "Maharashtra(India)")

    def test_state_db_table(self):
        """Test that state uses correct database table"""
        self.assertEqual(State._meta.db_table, "state")

    def test_state_field_constraints(self):
        """Test state field constraints"""
        state = State.objects.create(
            name="Test State", country=self.country, created_by=self.user
        )

        name_field = State._meta.get_field("name")
        self.assertEqual(name_field.max_length, 200)

        country_field = State._meta.get_field("country")
        self.assertEqual(country_field.related_model, Country)

        self.assertEqual(state.deleted, 0)

    def test_foreign_key_relationships(self):
        """Test foreign key relationships"""
        # Test country relationship
        country_field = State._meta.get_field("country")
        self.assertEqual(country_field.remote_field.on_delete.__name__, "CASCADE")

        # Test created_by relationship
        created_by_field = State._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(created_by_field.null)

        # Test updated_by relationship
        updated_by_field = State._meta.get_field("updated_by")
        self.assertEqual(updated_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(updated_by_field.null)


class StateAPITestCase(APITestCase):

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

        # Authenticate the test client
        self.client.force_authenticate(user=self.user)

    def test_list_states(self):
        """Test listing states"""
        url = reverse("state-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_states_no_pagination(self):
        """Test listing states without pagination"""
        url = reverse("state-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 1)

    def test_create_state(self):
        """Test creating a new state"""
        url = reverse("state-list")
        data = {"name": "Gujarat", "country": self.country.id}

        with patch("state.views.ActivityLog.log.state_create") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "State created successfully")

            # Verify the state was created
            state = State.objects.get(name="Gujarat")
            self.assertEqual(state.country, self.country)
            self.assertEqual(state.created_by, self.user)
            mock_log.assert_called_once()

    def test_create_state_invalid_data(self):
        """Test creating state with invalid data"""
        url = reverse("state-list")

        # Test empty name
        data = {"name": "", "country": self.country.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test missing country
        data = {"name": "Test State"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_create_duplicate_state(self):
        """Test creating duplicate state in same country"""
        url = reverse("state-list")
        data = {"name": "Maharashtra", "country": self.country.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_retrieve_state(self):
        """Test retrieving a specific state"""
        url = reverse("state-detail", args=[self.state.id])
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["name"], "Maharashtra")
        self.assertEqual(response.data["data"]["id"], self.state.id)

    def test_update_state(self):
        """Test updating a state"""
        url = reverse("state-detail", args=[self.state.id])
        data = {"name": "Maharashtra Updated"}

        # Modified: Removed unused mock_log variable
        with patch("state.views.ActivityLog.log.state_update", return_value=None):
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "State updated successfully")

            # Verify the state was updated
            self.state.refresh_from_db()
            self.assertEqual(self.state.name, "Maharashtra Updated")

    def test_update_state_invalid_data(self):
        """Test updating state with invalid data"""
        url = reverse("state-detail", args=[self.state.id])

        # Test empty name
        data = {"name": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_update_to_duplicate_state(self):
        """Test updating state to create duplicate"""
        # Create another state
        State.objects.create(name="Gujarat", country=self.country, created_by=self.user)

        url = reverse("state-detail", args=[self.state.id])
        data = {
            "name": "Gujarat",
            "country": self.country.id,
        }

        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_soft_delete_state(self):
        """Test soft deleting a state"""
        url = reverse("state-detail", args=[self.state.id])

        with patch("state.views.ActivityLog.log.state_archive") as mock_log:
            response = self.client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "State Deleted")

            # Verify the state was soft deleted
            self.state.refresh_from_db()
            self.assertEqual(self.state.deleted, 1)
            mock_log.assert_called_once()

    def test_delete_nonexistent_state(self):
        """Test deleting a non-existent state"""
        url = reverse("state-detail", args=[999])
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_states(self):
        """Test bulk deleting states"""
        # Create another state
        state2 = State.objects.create(
            name="Gujarat", country=self.country, created_by=self.user
        )

        url = reverse("state_archive-list")
        data = {"deleted": [self.state.id, state2.id]}

        with patch("state.views.ActivityLog.log.state_archive") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "States archived successfully")

            # Verify both states were archived
            self.state.refresh_from_db()
            state2.refresh_from_db()
            self.assertEqual(self.state.deleted, 1)
            self.assertEqual(state2.deleted, 1)
            mock_log.assert_called_once()

    def test_bulk_delete_nonexistent_state(self):
        """Test bulk deleting with non-existent state ID"""
        url = reverse("state_archive-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_list_archived_states(self):
        """Test listing archived states"""
        # Archive the state
        self.state.deleted = 1
        self.state.save()

        url = reverse("state_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertIsInstance(results_data["data"], list)
        else:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)

    def test_list_archived_states_no_pagination(self):
        """Test listing archived states without pagination"""
        # Archive the state
        self.state.deleted = 1
        self.state.save()

        url = reverse("state_archive-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "success" in response.data:
            self.assertTrue(response.data["success"])
            self.assertIsInstance(response.data["data"], list)
            self.assertGreaterEqual(len(response.data["data"]), 0)
        else:
            # Regular paginated response
            self.assertIn("results", response.data)

    def test_restore_states(self):
        """Test restoring archived states"""
        # Archive the state first
        self.state.deleted = 1
        self.state.save()

        url = reverse("state_restore-list")
        data = {"deleted": [self.state.id]}

        with patch("state.views.ActivityLog.log.state_restore") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "State restored successfully")

            # Verify the state was restore
            self.state.refresh_from_db()
            self.assertEqual(self.state.deleted, 0)
            mock_log.assert_called_once()

    def test_restore_nonexistent_state(self):
        """Test restoring non-existent state"""
        url = reverse("state_restore-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_search_states(self):
        """Test searching states"""
        url = reverse("state-list")
        response = self.client.get(url, {"search": "Maharashtra"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertEqual(len(results_data["data"]), 1)
            self.assertEqual(results_data["data"][0]["name"], "Maharashtra")
        else:
            self.assertTrue(response.data["success"])
            self.assertEqual(len(response.data["data"]), 1)
            self.assertEqual(response.data["data"][0]["name"], "Maharashtra")

    def test_search_states_by_country(self):
        """Test searching states by country name"""
        url = reverse("state-list")
        response = self.client.get(url, {"search": "India"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if "results" in response.data:
            results_data = response.data["results"]
            self.assertTrue(results_data["success"])
            self.assertGreaterEqual(len(results_data["data"]), 1)
        else:
            self.assertTrue(response.data["success"])
            self.assertGreaterEqual(len(response.data["data"]), 1)

    def test_ordering_states(self):
        """Test ordering states"""
        # Create another state for ordering test
        State.objects.create(
            name="Andhra Pradesh", country=self.country, created_by=self.user
        )

        url = reverse("state-list")
        response = self.client.get(
            url, {"ordering": "name", "no_pagination": "1"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        states = response.data["data"]
        self.assertEqual(states[0]["name"], "Andhra Pradesh")
        self.assertEqual(states[1]["name"], "Maharashtra")

    def test_unauthenticated_access(self):
        """Test accessing endpoints without authentication"""
        self.client.force_authenticate(user=None)

        url = reverse("state-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination(self):
        """Test pagination functionality"""
        # Create multiple states
        for i in range(5):
            State.objects.create(
                name=f"State {i}", country=self.country, created_by=self.user
            )

        url = reverse("state-list")
        response = self.client.get(url, {"page": 1, "page_size": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_serializer_write_only_fields(self):
        """Test that created_by and updated_by are write-only fields"""
        url = reverse("state-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]

        # These fields should not appear in the response due to write_only=True
        self.assertNotIn("created_by", data)
        self.assertNotIn("updated_by", data)

        # But country_name should be present as read-only field
        self.assertIn("country_name", data)
        self.assertEqual(data["country_name"], "India")

    def test_state_with_different_countries(self):
        """Test creating states with same name in different countries"""
        country2 = Country.objects.create(
            name="USA",
            code="US",
            unicode="🇺🇸",
            country_flag="https://example.com/us-flag.png",
            phone_code="+1",
            created_by=self.user,
        )
        # Create state with same name but different country
        url = reverse("state-list")
        data = {"name": "Maharashtra", "country": country2.id}

        # Modified: Removed unused mock_log variable
        with patch("state.views.ActivityLog.log.state_create", return_value=None):
            response = self.client.post(url, data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])

    def test_create_with_ip_address_logging(self):
        """Test that IP address is captured during creation"""
        url = reverse("state-list")
        data = {"name": "New State", "country": self.country.id}

        with patch("state.views.get_client_ip") as mock_get_ip, patch(
            "state.views.ActivityLog.log.state_create"
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
        url = reverse("state-detail", args=[self.state.id])
        data = {"name": "Updated State"}

        with patch("state.views.get_client_ip") as mock_get_ip, patch(
            "state.views.ActivityLog.log.state_update"
        ) as mock_log:

            mock_get_ip.return_value = "192.168.1.1"
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            mock_get_ip.assert_called_once()
            mock_log.assert_called_once()

    def test_state_validation_error_handling(self):
        """Test that validation errors are properly handled"""
        url = reverse("state-list")
        data = {"name": "Maharashtra", "country": self.country.id}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("message", response.data)

    def test_country_cascade_delete_affects_states(self):
        """Test that country relationship exists and cascade is configured"""
        country_field = State._meta.get_field("country")
        self.assertEqual(country_field.remote_field.on_delete.__name__, "CASCADE")

        # Test that the state is properly linked to country
        self.assertEqual(self.state.country, self.country)
        self.assertEqual(self.state.country.name, "India")
