# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from .models import PerformaInvoice, SubscriptionInvoice


# @receiver(post_save, sender=PerformaInvoice)
# def generate_invoice(sender, **kwargs):
#     performa_invoice = kwargs["instance"]
#     if kwargs["created"]:
#         invoice_number, financial_year = SubscriptionInvoice.get_invoice_number()
#         SubscriptionInvoice.objects.create(
#             performa_invoice=performa_invoice,
#             invoice_number=invoice_number,
#             invoice_year=financial_year,
#             price=performa_invoice.subscription.sell_price,
#             tax_perc=0.0,
#             remarks=performa_invoice.subscription.package_name,
#             created_by=performa_invoice.created_by,
#         )
