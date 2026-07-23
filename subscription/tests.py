from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from business_category.models import BusinessCategory
from subscription.models import PlanPrice, Subscription, SubscriptionFeature
from subscription.serializers_new import SubscriptionAPISerializer


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
        # Response is wrapped in success/data envelope
        self.assertIn("data", resp.data)
        self.assertIn("id", resp.data["data"])
        self.assertEqual(resp.data["data"]["package_name"], "Starter")

    def test_subscription_retrieve_update_delete(self):
        # create
        create = self.client.post(
            "/subscription/", self._create_subscription_payload(), format="json"
        )
        self.assertEqual(create.status_code, 201)
        sub_id = create.data["data"]["id"]

        # retrieve
        resp = self.client.get(f"/subscription/{sub_id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], sub_id)

        # update
        resp = self.client.patch(
            f"/subscription/{sub_id}/", {"package_name": "Starter Plus"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"]["package_name"], "Starter Plus")

        # delete (soft delete)
        resp = self.client.delete(f"/subscription/{sub_id}/")
        self.assertEqual(resp.status_code, 204)

        resp = self.client.get("/subscription/")
        self.assertEqual(resp.status_code, 200)

    def test_subscription_serializer_includes_requested_fields(self):
        subscription = Subscription.objects.create(
            package_name="Starter",
            description="Starter plan",
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )
        PlanPrice.objects.create(
            plan=subscription,
            period="monthly",
            price=500,
            duration_days=30,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Assessment",
            feature_code="assessment",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Resume Builder",
            feature_code="resume_builder",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )

        serializer = SubscriptionAPISerializer(subscription)
        data = serializer.data

        self.assertEqual(data["id"], subscription.id)
        self.assertEqual(data["package_name"], "Starter")
        self.assertEqual(data["subscription_price"], 500)
        self.assertEqual(data["duration_days"], 30)
        # Default is 0 since no value was set on creation
        self.assertEqual(data["no_of_profile_assessment"], 0)

    def test_subscription_get_payload_uses_expected_field_names(self):
        subscription = Subscription.objects.create(
            package_name="Vision Pro",
            description="fdgdfgdfgdfgdfg",
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )
        PlanPrice.objects.create(
            plan=subscription,
            period="monthly",
            price=25000,
            duration_days=25,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="career_compare",
            feature_code="career_compare",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="carrer_roadmap_path",
            feature_code="carrer_roadmap_path",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="ai_chat_access",
            feature_code="ai_chat_access",
            is_enabled=False,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Career Compare",
            feature_code="career_compare",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Career Roadmap Path",
            feature_code="career_roadmap",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Assessment",
            feature_code="assessment",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Monthly Token Allowance",
            feature_code="monthly_tokens",
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )

        serializer = SubscriptionAPISerializer(subscription)
        data = serializer.data

        self.assertEqual(data["package_name"], "Vision Pro")
        self.assertEqual(data["subscription_price"], 25000)
        self.assertEqual(data["subscription_discount"], 0)
        self.assertEqual(data["subscription_sell_price"], 25000)
        self.assertEqual(data["duration_days"], 25)
        # Defaults are 0 since no values were set on creation
        self.assertEqual(data["no_of_profile_assessment"], 0)
        self.assertEqual(data["no_of_tokens"], 0)
        # Features ordered by id; first created is lowercase "career_compare"
        self.assertEqual(
            data["subscription_feature"][0]["feature_name"], "career_compare"
        )
        self.assertEqual(data["subscription_feature"][0]["feature_status"], True)
        # Removed fields should NOT be present
        self.assertNotIn("price", data)
        self.assertNotIn("period", data)
        self.assertNotIn("discounted_price", data)
        self.assertNotIn("discount_amount", data)
        self.assertNotIn("portal_access", data)
        self.assertNotIn("prices", data)
        self.assertNotIn("country", data)
        self.assertNotIn("state", data)
        self.assertNotIn("country_name", data)
        self.assertNotIn("state_name", data)
        self.assertNotIn("subscription_features", data)

    # NOTE: subscription-status endpoint was removed in the new view implementation.
    # Skipped — no equivalent action exists in SubscriptionViewSet.
