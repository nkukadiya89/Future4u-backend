from django.contrib import admin

from subscription.models import (
    PaymentSubscription,
    Subscription,
    SubscriptionFeature,
    SubscriptionInvoice,
)

# Register your models here.
admin.site.register(Subscription)
admin.site.register(SubscriptionFeature)
admin.site.register(SubscriptionInvoice)
admin.site.register(PaymentSubscription)
