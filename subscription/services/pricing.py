# subscription/services/pricing.py

from datetime import timedelta

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


class PricingService:
    """Extract and persist pricing data for Subscription plans."""

    @staticmethod
    def extract(validated_data):
        """Pop pricing fields from validated_data and return as a dict."""
        price = validated_data.pop("subscription_price", None)
        if price is None:
            price = validated_data.pop("subscription_sell_price", None)
        if price is None:
            price = validated_data.pop("plan_price", None)
        discount = validated_data.pop("subscription_discount", None)
        duration = validated_data.pop("duration_days", None) or 30
        period = validated_data.pop("period", None)
        if not period:
            period = "yearly" if int(duration) >= 350 else "monthly"
        return {
            "price": price,
            "duration": duration,
            "period": period,
            "discount": discount,
        }

    @staticmethod
    def save(subscription, price_data, user, *, update=False):
        """Create or update PlanPrice and Discount for a subscription.

        When ``update=True``, old PlanPrice records are soft-deleted first.
        """
        price = price_data.get("price")
        duration = price_data.get("duration")
        period = price_data.get("period")
        discount = price_data.get("discount")

        if price is not None:
            if update:
                PlanPrice.objects.filter(plan=subscription, deleted=False).update(
                    deleted=True, deleted_by=user, deleted_at=now()
                )
            PlanPrice.objects.create(
                plan=subscription,
                period=period,
                price=price,
                duration_days=duration,
                created_by=user,
            )

        if discount is not None:
            existing_discount = None
            if update:
                existing_discount = Discount.objects.filter(
                    subscription=subscription,
                    discount_type="percent",
                    deleted=False,
                ).first()

            if existing_discount:
                existing_discount.value = float(discount)
                existing_discount.valid_from = now()
                existing_discount.valid_to = now() + timedelta(days=365 * 5)
                existing_discount.updated_by = user
                existing_discount.save()
            else:
                Discount.objects.create(
                    subscription=subscription,
                    name=f"{subscription.package_name} Discount",
                    discount_type="percent",
                    value=float(discount),
                    is_active=True,
                    valid_from=now(),
                    valid_to=now() + timedelta(days=365 * 5),
                    created_by=user,
                )
