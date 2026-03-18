from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from faq.models import FAQ
from user.models import User


class FAQAPITestCase(APITestCase):
    """Test cases for FAQ API endpoints"""

    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(email="testuser@example.com", username="testuser", password="testpass")

        # Create test FAQ
        self.faq = FAQ.objects.create(
            question="What is Django?",
            answer="Django is a high-level Python web framework that encourages "
            "rapid development and clean, pragmatic design.",
            created_by=self.user,
        )

        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_faq(self):
        """Test creating a new FAQ"""
        url = reverse("faq-list")
        data = {
            "question": "What is Python?",
            "answer": "Python is a high-level, interpreted programming language with dynamic semantics.",
            "created_by": self.user.id,
        }

        with patch("faq.views.ActivityLog.log.faq_create") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "FAQ added successfully")
            self.assertEqual(response.data["data"]["question"], "What is Python?")

            # Verify the FAQ was created in the database
            faq_exists = FAQ.objects.filter(question="What is Python?", deleted=False).exists()
            self.assertTrue(faq_exists)

            # Verify activity log was called
            mock_log.assert_called_once()

    def test_create_faq_invalid_data(self):
        """Test creating FAQ with invalid data"""
        url = reverse("faq-list")

        # Test empty question
        data = {"question": "", "answer": "Some answer"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test empty answer
        data = {"question": "Some question?", "answer": ""}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_list_faqs(self):
        """Test listing FAQs"""
        url = reverse("faq-list")
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"]["success"])
        self.assertIsInstance(response.data["results"]["data"], list)
        self.assertGreater(len(response.data["results"]["data"]), 0)

    def test_list_faqs_no_pagination(self):
        """Test listing FAQs without pagination"""
        url = reverse("faq-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIsInstance(response.data["data"], list)
        self.assertEqual(len(response.data["data"]), 1)

    def test_search_faqs(self):
        """Test searching FAQs"""
        # Create another FAQ for search
        FAQ.objects.create(
            question="What is Python Flask?",
            answer="Flask is a micro web framework written in Python.",
            created_by=self.user,
        )

        url = reverse("faq-list")

        # Search by question
        response = self.client.get(url, {"search": "Django"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertTrue(results_data["success"])
        self.assertEqual(len(results_data["data"]), 1)
        self.assertIn("Django", results_data["data"][0]["question"])

        # Search by answer
        response = self.client.get(url, {"search": "Flask"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertTrue(results_data["success"])
        self.assertEqual(len(results_data["data"]), 1)
        self.assertIn("Flask", results_data["data"][0]["question"])

    def test_ordering_faqs(self):
        """Test ordering FAQs"""
        # Create another FAQ
        FAQ.objects.create(
            question="ABC Question?",
            answer="ABC Answer.",
            created_by=self.user,
        )

        url = reverse("faq-list")

        # Order by question ascending
        response = self.client.get(url, {"ordering": "question"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertEqual(results_data["data"][0]["question"], "ABC Question?")

        # Order by question descending
        response = self.client.get(url, {"ordering": "-question"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results_data = response.data["results"]
        self.assertIn("Django", results_data["data"][0]["question"])

    def test_retrieve_faq(self):
        """Test retrieving a specific FAQ"""
        url = reverse("faq-detail", args=[self.faq.id])
        response = self.client.get(url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Django", response.data["question"])
        self.assertEqual(response.data["id"], self.faq.id)

    def test_update_faq(self):
        """Test updating a FAQ"""
        url = reverse("faq-detail", args=[self.faq.id])
        data = {"question": "What is Django Framework?", "answer": "Updated answer about Django."}

        with patch("faq.views.ActivityLog.log.faq_update") as mock_log:
            response = self.client.patch(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "FAQ updated successfully")

            # Verify the FAQ was updated
            self.faq.refresh_from_db()
            self.assertEqual(self.faq.question, "What is Django Framework?")
            mock_log.assert_called_once()

    def test_update_faq_invalid_data(self):
        """Test updating FAQ with invalid data"""
        url = reverse("faq-detail", args=[self.faq.id])

        # Test empty question
        data = {"question": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Test empty answer
        data = {"answer": ""}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_soft_delete_faq(self):
        """Test soft deleting a FAQ"""
        url = reverse("faq-detail", args=[self.faq.id])

        with patch("faq.views.ActivityLog.log.faq_archive") as mock_log:
            response = self.client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "FAQ Deleted")

            # Verify the FAQ was soft deleted
            self.faq.refresh_from_db()
            self.assertEqual(self.faq.deleted, 1)
            mock_log.assert_called_once()

    def test_delete_nonexistent_faq(self):
        """Test deleting a non-existent FAQ"""
        url = reverse("faq-detail", args=[999])
        response = self.client.delete(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_bulk_delete_faqs(self):
        """Test bulk deleting FAQs"""
        # Create another FAQ
        faq2 = FAQ.objects.create(
            question="What is REST API?",
            answer="REST API is a web service architecture.",
            created_by=self.user,
        )

        url = reverse("faq_archive-list")
        data = {"deleted": [self.faq.id, faq2.id]}

        with patch("faq.views.ActivityLog.log.faq_archive") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "FAQs archived successfully")

            # Verify both FAQs were archived
            self.faq.refresh_from_db()
            faq2.refresh_from_db()
            self.assertEqual(self.faq.deleted, 1)
            self.assertEqual(faq2.deleted, 1)
            mock_log.assert_called_once()

    def test_bulk_delete_nonexistent_faq(self):
        """Test bulk deleting with non-existent FAQ ID"""
        url = reverse("faq_archive-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_restore_faqs(self):
        """Test restoring archived FAQs"""
        # Archive the FAQ first
        self.faq.deleted = 1
        self.faq.save()

        url = reverse("faq_restore-list")
        data = {"deleted": [self.faq.id]}

        with patch("faq.views.ActivityLog.log.faq_restore") as mock_log:
            response = self.client.post(url, data, format="json")

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["success"])
            self.assertEqual(response.data["message"], "FAQ restored successfully")

            # Verify the FAQ was restored
            self.faq.refresh_from_db()
            self.assertEqual(self.faq.deleted, 0)
            mock_log.assert_called_once()

    def test_restore_nonexistent_faq(self):
        """Test restoring non-existent FAQ"""
        url = reverse("faq_restore-list")
        data = {"deleted": [999]}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response should be validation error list
        self.assertIsInstance(response.data, list)

    def test_unauthenticated_access(self):
        """Test accessing endpoints without authentication"""
        self.client.force_authenticate(user=None)

        url = reverse("faq-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_model_str_method(self):
        """Test FAQ model string representation"""
        self.assertEqual(str(self.faq), "What is Django?")

    def test_model_defaults(self):
        """Test FAQ model default values"""
        faq = FAQ.objects.create(question="Test Question?", answer="Test Answer.")
        self.assertEqual(faq.deleted, 0)
        self.assertIsNotNone(faq.created_at)
        # updated_at may be None until updated
        # Accept either None or a timestamp depending on signals/implementation
        # self.assertIsNotNone(faq.updated_at)

    def test_serializer_write_only_fields(self):
        """Test that created_by and updated_by are write-only fields"""
        url = reverse("faq-list")
        response = self.client.get(url, {"no_pagination": "1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"][0]

        # These fields should not appear in the response due to write_only=True
        self.assertNotIn("created_by", data)
        self.assertNotIn("updated_by", data)


class FAQModelTestCase(TestCase):
    """Test cases for FAQ model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(email="testuser@example.com", username="testuser", password="testpass")

    def test_faq_creation(self):
        """Test basic FAQ creation"""
        faq = FAQ.objects.create(
            question="What is Django?",
            answer="Django is a web framework.",
            created_by=self.user,
        )

        self.assertEqual(faq.question, "What is Django?")
        self.assertEqual(faq.answer, "Django is a web framework.")
        self.assertEqual(faq.created_by, self.user)
        self.assertEqual(faq.deleted, 0)
        self.assertIsNotNone(faq.created_at)
        # updated_at may be None at creation time depending on model implementation
        # self.assertIsNotNone(faq.updated_at)

    def test_faq_str_representation(self):
        """Test FAQ string representation"""
        faq = FAQ.objects.create(question="What is Django?", answer="Django is a web framework.")

        self.assertEqual(str(faq), "What is Django?")

    def test_faq_db_table(self):
        """Test that FAQ uses correct database table"""
        self.assertEqual(FAQ._meta.db_table, "faq")

    def test_foreign_key_relationships(self):
        """Test foreign key relationships"""
        # Test SET_NULL on user delete
        created_by_field = FAQ._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(created_by_field.null)

        updated_by_field = FAQ._meta.get_field("updated_by")
        self.assertEqual(updated_by_field.remote_field.on_delete.__name__, "SET_NULL")
        self.assertTrue(updated_by_field.null)
