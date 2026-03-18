from django.contrib import admin

from subscription.models import (PaymentSubscription, PurchasedSubscription,
                                 StripeCharge, Subcription,
                                 SubscriptionFeature, SubscriptionInvoice)

# Register your models here.

admin.site.register(Subcription)
admin.site.register(SubscriptionFeature)
admin.site.register(StripeCharge)
admin.site.register(PurchasedSubscription)
admin.site.register(SubscriptionInvoice)
admin.site.register(PaymentSubscription)
