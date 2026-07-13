# subscriptions/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from subscription.subscription_views import (
    PaymentSubscriptionViewSet,
    SubscriptionInvoiceViewSet,
    SubscriptionViewSet,
    UserSubscriptionViewSet,
    razorpay_webhook,
)

router = DefaultRouter()
router.register(r"subscriptions", SubscriptionViewSet, basename="subscriptions")
router.register(r"subscription", SubscriptionViewSet, basename="subscription")
router.register(
    r"company-subscriptions", UserSubscriptionViewSet, basename="company-subscriptions"
)
router.register(r"payments", PaymentSubscriptionViewSet, basename="payments")
router.register(r"invoices", SubscriptionInvoiceViewSet, basename="invoices")

urlpatterns = [
    # DRF routes
    path("", include(router.urls)),
    # webhook (must be outside router)
    path("razorpay/webhook/", razorpay_webhook, name="razorpay-webhook"),
]
