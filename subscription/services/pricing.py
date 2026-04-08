# subscription/services/pricing.py

from django.utils.timezone import now

from subscription.models import Discount, PromoCode


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


def calculate_price(subscription, promo_code=None):
    price = subscription.price
    discount = 0
    discount_obj = get_applicable_discount(subscription)

    if discount_obj:
        if discount_obj.discount_type == "percent":
            discount += (price * discount_obj.value) / 100
        else:
            discount += discount_obj.value
    promocode = (
        PromoCode.objects.filter(code=promo_code).first() if promo_code else None
    )

    if promocode:
        if promocode.subscription and promocode.subscription != subscription:
            raise Exception("Invalid promo for this plan")

        if not promocode.is_active:
            raise Exception("Promo inactive")

        if not (promocode.valid_from <= now() <= promocode.valid_to):
            raise Exception("Promo expired")

        if promocode.usage_limit and promocode.used_count >= promocode.usage_limit:
            raise Exception("Promo usage exceeded")

        if promocode.discount_type == "percent":
            discount += (price * promocode.value) / 100
        else:
            discount += promocode.value

    final_price = max(price - discount, 0)
    promocode.used_count += 1
    promocode.save()

    return {
        "price": price,
        "discount": discount,
        "final_price": final_price,
    }
