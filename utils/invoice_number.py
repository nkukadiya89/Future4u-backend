from django.db import transaction
from django.utils import timezone

from device_transfer.models import PaymentDeviceTransfer
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


def generate_subscription_invoice_number(company):
    current_year = timezone.now().year
    prefix = f"INV-{current_year}"

    with transaction.atomic():
        last_invoice = (
            PaymentSubscription.objects.filter(company=company, invoice_no__startswith=prefix)
            .select_for_update()
            .order_by("-invoice_no")
            .first()
        )

        if last_invoice and last_invoice.invoice_no.startswith(prefix):
            try:
                last_num = int(last_invoice.invoice_no.split("-")[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:02d}"


def generate_device_transfer_invoice_number(company):
    current_year = timezone.now().year
    prefix = f"DT-{current_year}"

    with transaction.atomic():
        last_invoice = (
            PaymentDeviceTransfer.objects.filter(company=company, invoice_no__startswith=prefix)
            .select_for_update()
            .order_by("-invoice_no")
            .first()
        )

        if last_invoice and last_invoice.invoice_no.startswith(prefix):
            try:
                last_num = int(last_invoice.invoice_no.split("-")[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:02d}"
