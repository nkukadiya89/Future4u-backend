from subscription.models import PaymentSubscription, SubscriptionInvoice


def generate_invoice(self):
    last_invoice = SubscriptionInvoice.objects.order_by("-id").first()

    if last_invoice and last_invoice.invoice_number:
        last_invoice_number = int(last_invoice.invoice_number) + 10
    else:
        last_invoice_number = 1

    invoice_number = "{:02d}".format(last_invoice_number)

    return invoice_number


def generate_invoice_number(self):
    last_invoice = SubscriptionInvoice.objects.order_by("-id").first()

    if last_invoice and last_invoice.invoice_number:
        last_invoice_number = int(last_invoice.invoice_number) + 1
    else:
        last_invoice_number = 1

    invoice_number = "{:04d}".format(last_invoice_number)

    return invoice_number


def generate_subscription_payment_invoice_number():
    last_invoice = PaymentSubscription.objects.order_by("-invoice_no").first()

    if last_invoice and last_invoice.invoice_no:
        last_invoice_number = int(last_invoice.invoice_no) + 1
    else:
        last_invoice_number = 1

    return "{:04d}".format(last_invoice_number)
