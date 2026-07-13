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
            value="5",
            is_unlimited=False,
            is_core=True,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Resume Builder",
            feature_code="resume_builder",
            is_unlimited=True,
            is_core=False,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )

        serializer = SubscriptionAPISerializer(subscription)
        data = serializer.data

        self.assertEqual(data["id"], subscription.id)
        self.assertEqual(data["package_name"], "Starter")
        self.assertEqual(data["price"], 500)
        self.assertEqual(data["period"], "monthly")
        self.assertEqual(data["duration_days"], 30)
        self.assertEqual(data["no_of_profile_assessment"], 5)
        self.assertIsNone(data["country"])
        self.assertIsNone(data["state"])
        self.assertIsNone(data["country_name"])
        self.assertIsNone(data["state_name"])
        self.assertIn("assessment", data["portal_access"])
        self.assertIn("resume_builder", data["portal_access"])
        self.assertTrue(data["portal_access"]["assessment"])
        self.assertTrue(data["portal_access"]["resume_builder"])

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
            value=None,
            is_unlimited=False,
            is_core=True,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="carrer_roadmap_path",
            feature_code="carrer_roadmap_path",
            value=None,
            is_unlimited=False,
            is_core=True,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="ai_chat_access",
            feature_code="ai_chat_access",
            value=None,
            is_unlimited=False,
            is_core=True,
            is_enabled=False,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Career Compare",
            feature_code="career_compare",
            value=None,
            is_unlimited=False,
            is_core=False,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Career Roadmap Path",
            feature_code="career_roadmap",
            value=None,
            is_unlimited=False,
            is_core=False,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Assessment",
            feature_code="assessment",
            value="50",
            is_unlimited=False,
            is_core=False,
            is_enabled=True,
            created_by=self.user,
            updated_by=self.user,
        )
        SubscriptionFeature.objects.create(
            subscription=subscription,
            feature_name="Tokens",
            feature_code="tokens",
            value="60",
            is_unlimited=False,
            is_core=False,
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
        self.assertEqual(data["plan_price"], 25000)
        self.assertEqual(data["duration_days"], 25)
        self.assertEqual(data["no_of_profile_assessment"], 50)
        self.assertEqual(data["no_of_tokens"], 60)
        self.assertEqual(data["core_features"][0]["feature_name"], "career_compare")
        self.assertEqual(data["core_features"][2]["feature_status"], False)
        self.assertEqual(
            data["subscription_feature"][0]["feature_name"], "Career Compare"
        )
        self.assertEqual(data["subscription_feature"][0]["feature_status"], True)

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
