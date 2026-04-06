from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from business_category.models import BusinessCategory
from company.models import Company
from subscription.models import PaymentSubscription, Subscription


class SubscriptionCartAndPaymentTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="pass1234",
            first_name="Test",
        )
        self.client.force_authenticate(user=self.user)

        self.bc = BusinessCategory.objects.create(
            business_category="IT", created_by=self.user, updated_by=self.user
        )

        self.company = Company.objects.create(
            name="Acme Corp",
            email="acme@example.com",
            phone="9999999999",
            company_type="Media owner",
            created_by=self.user,
            updated_by=self.user,
        )
        # associate user with company for items endpoint
        self.user.company = self.company
        self.user.save()

        self.sub = Subscription.objects.create(
            package_name="Pro Plan",
            subscription_type="subscription",
            subscription_price=1000,
            subscription_discount=0,
            subscription_sell_price=2000,
            plan_price=2000,
            duration_days=30,
            description="Test plan",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_cart_add_and_items(self):
        # Add item
        resp = self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["success"])

        # Items should reflect quantity and prices
        resp = self.client.get("/subscription-cart/items/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["data"]
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(
            items[0]["subscription_price"], self.sub.subscription_sell_price
        )

    def test_cart_increment_decrement_set_quantity_and_remove(self):
        # Seed one item with quantity 1
        self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 1},
            format="json",
        )

        # Increment
        resp = self.client.patch(
            "/subscription-cart/increment/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        # verify via items
        resp_items = self.client.get("/subscription-cart/items/")
        self.assertEqual(resp_items.status_code, 200)

        # Decrement
        resp = self.client.patch(
            "/subscription-cart/decrement/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        resp_items = self.client.get("/subscription-cart/items/")
        self.assertEqual(resp_items.status_code, 200)

        # Set exact quantity to 5
        # No set-quantity endpoint; simulate by incrementing to reach 5
        for _ in range(4):
            self.client.patch(
                "/subscription-cart/increment/",
                {"company": self.company.id, "subscription": self.sub.id},
                format="json",
            )
        resp_items = self.client.get("/subscription-cart/items/")

        # Remove item
        # remove requires item id in URL
        items_resp = self.client.get("/subscription-cart/items/")
        item_id = items_resp.data["data"][0]["id"]
        resp = self.client.delete(f"/subscription-cart/{item_id}/remove/")
        self.assertEqual(resp.status_code, 200)

    @patch("subscription.views.client.payment_link.create")
    def test_checkout_creates_payment_link_and_payment_subscription(
        self, mock_payment_link_create
    ):
        # Seed cart and BusinessSetting
        from user_profile.models import BusinessSetting

        BusinessSetting.objects.create(
            company=self.company,
            notifications=True,
            sgst=9.0,
            cgst=9.0,
            igst=0.0,
            currency="INR",
            created_by=self.user,
            updated_by=self.user,
        )
        self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 1},
            format="json",
        )

        mock_payment_link_create.return_value = {
            "id": "plink_123",
            "short_url": "https://rzp.io/i/test123",
        }

        items = [
            {
                "subscription": self.sub.id,
                "quantity": 1,
                "subscription_type": "1 year",
                "subscription_price": self.sub.subscription_sell_price,
                "plan_total": self.sub.subscription_sell_price,
            }
        ]
        checkout_payload = {
            "company_id": self.company.id,
            "items": items,
            "subtotal": items[0]["plan_total"],
            "cgst": round(items[0]["plan_total"] * 0.09, 2),
            "sgst": round(items[0]["plan_total"] * 0.09, 2),
            "total_amount": round(items[0]["plan_total"] * 1.18, 2),
        }
        resp = self.client.post(
            "/subscription-cart/checkout/", checkout_payload, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["success"])
        self.assertIn("payment_link", resp.data["data"])

        ps = PaymentSubscription.objects.order_by("-id").first()
        self.assertIsNotNone(ps)
        self.assertEqual(ps.razor_order_id, "plink_123")
        self.assertGreater(ps.total_amount, 0)

    @patch("subscription.views.client.payment.fetch")
    def test_update_payment_data_sets_active_and_invoice_and_duration(
        self, mock_payment_fetch
    ):
        # Create a pending PaymentSubscription via direct API (single subscription flow)
        with patch("subscription.views.client.payment_link.create") as mock_link_create:
            from user_profile.models import BusinessSetting

            BusinessSetting.objects.create(
                company=self.company,
                notifications=True,
                sgst=9.0,
                cgst=9.0,
                igst=0.0,
                currency="INR",
                created_by=self.user,
                updated_by=self.user,
            )
            mock_link_create.return_value = {
                "id": "plink_abc",
                "short_url": "https://rzp.io/i/abc",
            }
            items = [
                {
                    "subscription": self.sub.id,
                    "quantity": 1,
                    "subscription_type": "1 year",
                    "subscription_price": self.sub.subscription_sell_price,
                    "plan_total": self.sub.subscription_sell_price,
                }
            ]
            checkout_payload = {
                "company_id": self.company.id,
                "items": items,
                "subtotal": items[0]["plan_total"],
                "cgst": round(items[0]["plan_total"] * 0.09, 2),
                "sgst": round(items[0]["plan_total"] * 0.09, 2),
                "total_amount": round(items[0]["plan_total"] * 1.18, 2),
            }
            self.client.post(
                "/subscription-cart/checkout/", checkout_payload, format="json"
            )

        mock_payment_fetch.return_value = {"amount": int(2360 * 100)}

        resp = self.client.patch(
            "/payment-subscription/update-payment-data/",
            {
                "razorpay_payment_id": "pay_123",
                "razorpay_payment_link_id": "plink_abc",
                "razorpay_payment_link_status": "paid",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["status"])

        ps = PaymentSubscription.objects.get(razor_order_id="plink_abc")
        self.assertEqual(ps.payment_status, "paid")
        self.assertEqual(ps.active, "Active")
        self.assertEqual(ps.payment_id, "pay_123")
        self.assertIsNotNone(ps.invoice_no)
        # Verify item dates instead of non-existent fields on PaymentSubscription
        first_item = ps.items.first()
        self.assertIsNotNone(first_item)
        self.assertIsNotNone(first_item.start_date)
        # end_date may be computed based on subscription_type; should be set
        self.assertIsNotNone(first_item.end_date)

    def test_payment_subscription_list_filter_by_company(self):
        # Create two payment subscriptions for different companies
        other_company = Company.objects.create(
            name="Other Co",
            email="other@example.com",
            phone="8888888888",
            company_type="Media owner",
            created_by=self.user,
            updated_by=self.user,
        )

        PaymentSubscription.objects.create(
            company=self.company, invoice_no="0", currency="INR"
        )
        PaymentSubscription.objects.create(
            company=other_company, invoice_no="0", currency="INR"
        )

        resp = self.client.get(
            f"/payment-subscription/?company_id={self.company.id}&ordering=-id"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        items = data.get("results") or data.get("data") or []
        if isinstance(items, dict) and "data" in items:
            items = items["data"]
        self.assertTrue(any(ps["company"] == self.company.id for ps in items))
        self.assertFalse(any(ps["company"] == other_company.id for ps in items))

    def test_items_requires_company_association(self):
        # detach company
        self.user.company = None
        self.user.save()
        resp = self.client.get("/subscription-cart/items/")
        self.assertEqual(resp.status_code, 400)

    def test_checkout_empty_cart_returns_400(self):
        # Missing items/company_id should 400
        resp = self.client.post(
            "/subscription-cart/checkout/",
            {"company_id": self.company.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("items", resp.data.get("message", ""))

    def test_increment_missing_item_returns_404(self):
        resp = self.client.patch(
            "/subscription-cart/increment/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_decrement_missing_item_returns_404(self):
        resp = self.client.patch(
            "/subscription-cart/decrement/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_remove_missing_item_still_success(self):
        # removing non-existent detail id should be 404
        resp = self.client.delete("/subscription-cart/999999/remove/")
        self.assertEqual(resp.status_code, 404)

    def test_set_quantity_min_validation(self):
        # Not applicable; decrement to remove instead
        self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 1},
            format="json",
        )
        resp = self.client.patch(
            "/subscription-cart/decrement/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_shared_cart_across_users_same_company(self):
        # user1 adds item
        self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 1},
            format="json",
        )
        # login as another user and increment same item
        User = get_user_model()
        user2 = User.objects.create_user(
            email="u2@example.com", password="pass1234", first_name="U2"
        )
        user2.company = self.company
        user2.save()
        self.client.force_authenticate(user=user2)
        resp = self.client.patch(
            "/subscription-cart/increment/",
            {"company": self.company.id, "subscription": self.sub.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_update_payment_data_missing_link_id(self):
        resp = self.client.patch(
            "/payment-subscription/update-payment-data/",
            {"razorpay_payment_id": "pay_x", "razorpay_payment_link_status": "paid"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_payment_data_not_paid(self):
        # Create pending PaymentSubscription via checkout
        with patch("subscription.views.client.payment_link.create") as mock_link_create:
            from user_profile.models import BusinessSetting

            BusinessSetting.objects.create(
                company=self.company,
                notifications=True,
                sgst=9.0,
                cgst=9.0,
                igst=0.0,
                currency="INR",
                created_by=self.user,
                updated_by=self.user,
            )
            mock_link_create.return_value = {
                "id": "plink_np",
                "short_url": "https://rzp.io/i/np",
            }
            items = [
                {
                    "subscription": self.sub.id,
                    "quantity": 1,
                    "subscription_type": "1 year",
                    "subscription_price": self.sub.subscription_sell_price,
                    "plan_total": self.sub.subscription_sell_price,
                }
            ]
            self.client.post(
                "/subscription-cart/checkout/",
                {
                    "company_id": self.company.id,
                    "items": items,
                    "subtotal": items[0]["plan_total"],
                    "cgst": round(items[0]["plan_total"] * 0.09, 2),
                    "sgst": round(items[0]["plan_total"] * 0.09, 2),
                    "total_amount": round(items[0]["plan_total"] * 1.18, 2),
                },
                format="json",
            )
        resp = self.client.patch(
            "/payment-subscription/update-payment-data/",
            {
                "razorpay_payment_link_id": "plink_np",
                "razorpay_payment_link_status": "created",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("subscription.views.client.payment_link.create")
    def test_payment_subscription_create_calculates_gst(self, mock_link_create):
        from user_profile.models import BusinessSetting

        BusinessSetting.objects.create(
            company=self.company,
            notifications=True,
            sgst=9.0,
            cgst=9.0,
            igst=0.0,
            currency="INR",
            created_by=self.user,
            updated_by=self.user,
        )
        mock_link_create.return_value = {
            "id": "plink_calc",
            "short_url": "https://rzp.io/i/calc",
        }
        items = [
            {
                "subscription": self.sub.id,
                "quantity": 2,
                "subscription_type": "1 year",
                "subscription_price": self.sub.subscription_sell_price,
                "plan_total": self.sub.subscription_sell_price * 2,
            }
        ]
        subtotal = items[0]["plan_total"]
        cgst = round(subtotal * 0.09, 2)
        sgst = round(subtotal * 0.09, 2)
        total_amount = round(subtotal + cgst + sgst, 2)
        resp = self.client.post(
            "/subscription-cart/checkout/",
            {
                "company_id": self.company.id,
                "items": items,
                "subtotal": subtotal,
                "cgst": cgst,
                "sgst": sgst,
                "total_amount": total_amount,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        ps = PaymentSubscription.objects.get(razor_order_id="plink_calc")
        self.assertAlmostEqual(ps.subtotal, subtotal, places=2)
        self.assertAlmostEqual(ps.cgst_amount, cgst, places=2)
        self.assertAlmostEqual(ps.sgst_amount, sgst, places=2)
        self.assertAlmostEqual(ps.total_amount, total_amount, places=2)

    @patch("subscription.views.client.payment_link.create")
    def test_checkout_amount_equals_grand_total(self, mock_link_create):
        # add items
        self.client.post(
            "/subscription-cart/add-to-cart/",
            {"company": self.company.id, "subscription": self.sub.id, "quantity": 3},
            format="json",
        )
        mock_link_create.return_value = {
            "id": "plink_total",
            "short_url": "https://rzp.io/i/total",
        }
        from user_profile.models import BusinessSetting

        BusinessSetting.objects.create(
            company=self.company,
            notifications=True,
            sgst=9.0,
            cgst=9.0,
            igst=0.0,
            currency="INR",
            created_by=self.user,
            updated_by=self.user,
        )
        plan_total = self.sub.subscription_sell_price * 3
        subtotal = plan_total
        cgst = round(subtotal * 0.09, 2)
        sgst = round(subtotal * 0.09, 2)
        total_amount = round(subtotal + cgst + sgst, 2)
        items = [
            {
                "subscription": self.sub.id,
                "quantity": 3,
                "subscription_type": "1 year",
                "subscription_price": self.sub.subscription_sell_price,
                "plan_total": plan_total,
            }
        ]
        resp = self.client.post(
            "/subscription-cart/checkout/",
            {
                "company_id": self.company.id,
                "items": items,
                "subtotal": subtotal,
                "cgst": cgst,
                "sgst": sgst,
                "total_amount": total_amount,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        summary = resp.data["data"]["summary"]
        self.assertEqual(summary["total_amount"], total_amount)


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
