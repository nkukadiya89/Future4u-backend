from rest_framework.routers import DefaultRouter

from subscription.views import PaymentSubscriptionViewSet, SubscriptionViewSet

subscription_router = DefaultRouter()
subscription_router.register(
    "subscription", SubscriptionViewSet, basename="subscription"
)
subscription_router.register(
    "payment-subscription", PaymentSubscriptionViewSet, basename="payment-subscription"
)
