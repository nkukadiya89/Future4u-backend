from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from business_category.models import BusinessCategory


class SubscriptionMasterTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="mastertester@example.com", password="pass1234", first_name="Master"
        )
        self.client.force_authenticate(user=self.user)

        # Category optional; keep available if needed
        self.bc = BusinessCategory.objects.create(
            business_category="IT", created_by=self.user, updated_by=self.user
        )

    def _create_subscription_payload(self):
        return {
            "package_name": "Starter",
            "subscription_type": "subscription",
            "subscription_price": 500,
            "subscription_discount": 0,
            "subscription_sell_price": 1000,
            "plan_price": 1500,
            "duration_days": 30,
            "description": "Starter plan",
        }

    def test_subscription_create(self):
        resp = self.client.post(
            "/subscription/", self._create_subscription_payload(), format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data.get("success"))

    def test_subscription_retrieve_update_delete(self):
        # create
        create = self.client.post(
            "/subscription/", self._create_subscription_payload(), format="json"
        )
        sub_id = create.data["data"]["id"]

        # retrieve
        resp = self.client.get(f"/subscription/{sub_id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["id"], sub_id)

        # update
        resp = self.client.patch(
            f"/subscription/{sub_id}/", {"package_name": "Starter Plus"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["package_name"], "Starter Plus")

        # delete (soft delete)
        resp = self.client.delete(f"/subscription/{sub_id}/")
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/subscription/")
        self.assertEqual(resp.status_code, 200)

    def test_subscription_status_update(self):
        create = self.client.post(
            "/subscription/", self._create_subscription_payload(), format="json"
        )
        sub_id = create.data["data"]["id"]

        # set active
        resp = self.client.patch(
            f"/subscription/{sub_id}/subscription-status/",
            {"status": "active"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # set inactive
        resp = self.client.patch(
            f"/subscription/{sub_id}/subscription-status/",
            {"status": "in_active"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
