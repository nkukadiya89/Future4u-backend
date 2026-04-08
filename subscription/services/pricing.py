# subscription/services/pricing.py

from django.utils.timezone import now

from subscription.models import Discount


def get_applicable_discount(subscription):
    current_time = now()

    # plan-specific
    discount = (
        Discount.objects.filter(
            subscription=subscription,
            is_active=True,
            valid_from__lte=current_time,
            valid_to__gte=current_time,
        )
        .order_by("-id")
        .first()
    )

    if discount:
        return discount

    # global
    return (
        Discount.objects.filter(
            subscription__isnull=True,
            is_active=True,
            valid_from__lte=current_time,
            valid_to__gte=current_time,
        )
        .order_by("-id")
        .first()
    )


def calculate_price(subscription):
    price = subscription.price
    discount_obj = get_applicable_discount(subscription)

    if not discount_obj:
        return {
            "price": price,
            "discount": 0,
            "final_price": price,
        }

    if discount_obj.discount_type == "percent":
        discount = (price * discount_obj.value) / 100
    else:
        discount = discount_obj.value

    final_price = max(price - discount, 0)

    return {
        "price": price,
        "discount": discount,
        "final_price": final_price,
    }
