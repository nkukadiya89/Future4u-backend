# subscription/services/pricing.py

from django.utils.timezone import now

from subscription.models import Discount, PromoCode, PlanPrice, Subscription


def get_applicable_discount(target):
    """Return applicable Discount for a Subscription or PlanPrice.

    `target` can be a `Subscription` or `PlanPrice` instance.
    """
    current_time = now()

    subscription = None
    if isinstance(target, PlanPrice):
        subscription = target.plan
    elif isinstance(target, Subscription):
        subscription = target
    else:
        subscription = None

    # plan-specific
    if subscription:
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


def calculate_price(target, promocode=None):
    """Calculate price and discount for a Subscription or PlanPrice.

    Returns dict with keys: price, discount, final_price, promo_code_applied
    """
    # determine price source
    if isinstance(target, PlanPrice):
        price = target.price
    elif isinstance(target, Subscription):
        # fallback: choose the first active price for subscription
        pp = (
            PlanPrice.objects.filter(plan=target, is_active=True, deleted=False)
            .order_by("-price")
            .first()
        )
        if not pp:
            raise Exception("No active PlanPrice found for this subscription")
        price = pp.price
    else:
        raise Exception("Unsupported target for pricing")
    discount = 0
    discount_obj = get_applicable_discount(target)

    if discount_obj:
        if discount_obj.discount_type == "percent":
            discount += (price * discount_obj.value) / 100
        else:
            discount += discount_obj.value
    promo_code_applied = False

    if promocode:
        # promocode.subscription may be null (global) or a Subscription instance
        if promocode.subscription and isinstance(target, PlanPrice):
            if promocode.subscription != target.plan:
                raise Exception("Invalid promo for this plan")
        elif promocode.subscription and isinstance(target, Subscription):
            if promocode.subscription != target:
                raise Exception("Invalid promo for this plan")

        if not promocode.is_active:
            raise Exception("Promo inactive")

        if not (promocode.valid_from <= now() <= promocode.valid_to):
            raise Exception("Promo expired")

        if promocode.usage_limit and promocode.used_count >= promocode.usage_limit:
            raise Exception("Promo usage exceeded")

        if promocode.discount_type == "percent":
            discount += (price * promocode.value) / 100
            promo_code_applied = True
        else:
            discount += promocode.value
            promo_code_applied = True

    final_price = max(price - discount, 0)

    return {
        "price": price,
        "discount": discount,
        "final_price": final_price,
        "promo_code_applied": promo_code_applied,
    }
