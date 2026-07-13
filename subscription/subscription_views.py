import hashlib
import hmac
import json
from datetime import timedelta

import razorpay
from decouple import config
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from subscription.models import FeatureUsage, SubscriptionFeature
from subscription.serializers_new import (PaymentSubscriptionSerializer,
                                          SubscriptionAPISerializer,
                                          SubscriptionInvoiceSerializer,
                                          SubscriptionSerializer,
                                          UserSubscriptionSerializer)
from subscription.services.pricing import calculate_price

from .models import (PaymentSubscription, PlanPrice, PromoCode, Subscription,
                     SubscriptionInvoice, UserSubscription)


class SubscriptionViewSet(ModelViewSet):
    queryset = Subscription.objects.filter(is_active=True)
    serializer_class = SubscriptionAPISerializer
    http_method_names = ["get", "head", "options"]

    def get_serializer_class(self):
        return SubscriptionAPISerializer


class UserSubscriptionViewSet(ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        qs = super().get_queryset()
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        user = request.user
        user_sub = (
            UserSubscription.objects.filter(user=user, is_active=True)
            .select_related("plan_price__plan")
            .first()
        )

        if not user_sub:
            return Response({"subscription": None})

        # default feature to report (assessment)
        feature_code = "assessment"
        plan = getattr(user_sub.plan_price, "plan", None)
        feature = SubscriptionFeature.objects.filter(
            subscription=plan,
            feature_code=feature_code,
            is_enabled=True,
            deleted=False,
        ).first()

        usage = FeatureUsage.objects.filter(
            user=user, feature_code=feature_code, plan_price=user_sub.plan_price
        ).first()

        used = usage.used if usage else 0

        if feature:
            allowed = "unlimited" if feature.is_unlimited else int(feature.value or 0)
            remaining = None if feature.is_unlimited else max(allowed - used, 0)
        else:
            allowed = 0
            remaining = 0

        return Response(
            {
                "subscription": plan.package_name if plan else None,
                "period": user_sub.plan_price.period if user_sub.plan_price else None,
                "start_date": user_sub.start_date,
                "end_date": user_sub.end_date,
                "features": {
                    feature_code: {"allowed": allowed, "used": used, "remaining": remaining}
                },
            }
        )


class PaymentSubscriptionViewSet(ModelViewSet):
    queryset = PaymentSubscription.objects.all()
    serializer_class = PaymentSubscriptionSerializer
    client = razorpay.Client(
        auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_SECRET"))
    )

    def perform_create(self, serializer):
        # create pending payment (acts like cart)
        serializer.save(status="pending")

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """
        This simulates webhook success (in real case use Razorpay webhook)
        """
        payment = self.get_object()

        if payment.status == "paid":
            return Response({"detail": "Already paid"}, status=400)

        payment.status = "paid"
        payment.payment_date = now()
        payment.razorpay_payment_id = request.data.get("payment_id")
        payment.save()

        # activate or renew subscription using plan_price
        plan_price = payment.plan_price
        if not plan_price:
            return Response({"detail": "No plan price associated with payment"}, status=400)

        duration = plan_price.duration_days

        user_sub, created = UserSubscription.objects.get_or_create(
            user=payment.user,
            plan_price=plan_price,
            defaults={
                "start_date": now().date(),
                "end_date": now().date() + timedelta(days=duration),
                "is_active": True,
            },
        )

        if not created:
            # renewal logic
            user_sub.end_date = max(user_sub.end_date, now().date()) + timedelta(
                days=duration
            )
            user_sub.is_active = True
            user_sub.save()

        # Reset feature usage so user gets fresh tokens for new billing period
        FeatureUsage.objects.filter(user=payment.user).update(used=0)

        return Response({"detail": "Payment successful"})

    @action(detail=False, methods=["post"], url_path="create-order")
    def create_order(self, request):
        # Accept either `plan_price_id` (preferred) or legacy `subscription_id`
        plan_price_id = request.data.get("plan_price_id")
        subscription_id = request.data.get("subscription_id")
        promo_code_str = request.data.get("promo_code")
        user = request.user

        promocode = (
            PromoCode.objects.filter(code=promo_code_str).first()
            if promo_code_str
            else None
        )

        # Resolve plan_price
        plan_price = None
        if plan_price_id:
            plan_price = PlanPrice.objects.filter(id=plan_price_id, deleted=False).first()
            if not plan_price:
                return Response({"success": False, "message": "Invalid plan_price_id"}, status=400)
        elif subscription_id:
            subscription = Subscription.objects.filter(id=subscription_id, deleted=False).first()
            if not subscription:
                return Response({"success": False, "message": "Invalid subscription"}, status=400)
            # pick default active price
            plan_price = (
                PlanPrice.objects.filter(plan=subscription, is_active=True, deleted=False)
                .order_by("-price")
                .first()
            )
            if not plan_price:
                return Response({"success": False, "message": "No active prices for subscription"}, status=400)

        try:
            pricing = calculate_price(plan_price, promocode)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

        amount = pricing["price"]
        discount = pricing["discount"]
        final_amount = pricing["final_price"]
        promocode_applied = pricing.get("promo_code_applied", False)

        if promocode_applied and promocode:
            promocode.used_count += 1
            promocode.save()

        # create razorpay order
        order = self.client.order.create(
            {
                "amount": int(final_amount * 100),  # in paise
                "currency": "INR",
                "payment_capture": 1,
            }
        )

        # store in DB
        payment = PaymentSubscription.objects.create(
            user=user,
            plan_price=plan_price,
            amount=amount,
            discount_amount=discount,
            final_amount=final_amount,
            status="pending",
            razorpay_order_id=order["id"],
            currency="INR",
            promocode=promocode.code if promocode else None,
        )

        return Response(
            {
                "success": True,
                "data": {
                    "order_id": order["id"],
                    "amount": final_amount,
                    "payment_id": payment.id,
                    "key": config("RAZORPAY_KEY_ID"),
                },
            }
        )


class SubscriptionInvoiceViewSet(ModelViewSet):
    queryset = SubscriptionInvoice.objects.all()
    serializer_class = SubscriptionInvoiceSerializer

    @action(detail=True, methods=["post"])
    def mark_final(self, request, pk=None):
        invoice = self.get_object()

        if invoice.invoice_type == "final":
            return Response({"detail": "Already final"}, status=400)

        with transaction.atomic():
            # generate invoice number here (use FinancialYearModel)
            get_current_year = FinancialYearModel.get_current_financial_year()

            last_invoice = (
                SubscriptionInvoice.objects.select_for_update()
                .filter(invoice_type="final")
                .filter(
                    created_at__range=(
                        get_current_year.start_date,
                        get_current_year.end_date,
                    )
                )
                .order_by("-id")
                .first()
            )

            # invoice_number is in format 0001/25-26, 0002/25-26, ... reset every financial year i.e 0001/26-27 for next year
            last_number = (
                int(last_invoice.invoice_number.split("/")[0])
                if last_invoice and last_invoice.invoice_number
                else 0
            )

            next_number = (int(last_number) + 1) if last_invoice and last_number else 1
            next_number_str = (
                str(next_number).zfill(4) + f"/{get_current_year.financial_year}"
            )

            invoice.invoice_number = next_number_str
            invoice.invoice_type = "final"
            invoice.save()

        return Response({"detail": "Invoice finalized"})


@csrf_exempt
def razorpay_webhook(request):
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

    body = request.body
    received_signature = request.headers.get("X-Razorpay-Signature")

    # Verify signature
    expected_signature = hmac.new(
        bytes(webhook_secret, "utf-8"), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        return HttpResponse(status=400)

    payload = json.loads(body)

    event = payload.get("event")

    # Handle only successful payment
    if event == "payment.captured":
        payment_data = payload["payload"]["payment"]["entity"]

        razorpay_payment_id = payment_data["id"]
        razorpay_order_id = payment_data["order_id"]
        method = payment_data.get("method")
        amount = payment_data["amount"] / 100  # paise to rupees

        try:
            payment = PaymentSubscription.objects.get(
                razorpay_order_id=razorpay_order_id
            )
        except PaymentSubscription.DoesNotExist:
            return HttpResponse(status=404)

        # Idempotency check (VERY IMPORTANT)
        if payment.status == "paid":
            return HttpResponse(status=200)

        # Update payment
        payment.status = "paid"
        payment.razorpay_payment_id = razorpay_payment_id
        payment.payment_date = now()
        payment.payment_method = method
        payment.amount = amount
        payment.save()

        # Activate / renew subscription using plan_price
        plan_price = payment.plan_price
        if not plan_price:
            return HttpResponse(status=400)

        duration = plan_price.duration_days

        user_sub, created = UserSubscription.objects.get_or_create(
            user=payment.user,
            plan_price=plan_price,
            defaults={
                "start_date": now().date(),
                "end_date": now().date() + timedelta(days=duration),
                "is_active": True,
            },
        )

        if not created:
            user_sub.end_date = max(user_sub.end_date, now().date()) + timedelta(
                days=duration
            )
            user_sub.is_active = True
            user_sub.save()

        # Reset feature usage so user gets fresh tokens for new billing period
        FeatureUsage.objects.filter(user=payment.user).update(used=0)

    return HttpResponse(status=200)
