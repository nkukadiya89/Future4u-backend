from django.contrib import admin

from subscription.models import (
    PaymentSubscription,
    Subscription,
    SubscriptionCart,
    SubscriptionCartWithSite,
    SubscriptionFeature,
    SubscriptionInvoice,
)

# Register your models here.
admin.site.register(Subscription)
admin.site.register(SubscriptionFeature)
admin.site.register(SubscriptionInvoice)
admin.site.register(PaymentSubscription)
admin.site.register(SubscriptionCart)
admin.site.register(SubscriptionCartWithSite)
