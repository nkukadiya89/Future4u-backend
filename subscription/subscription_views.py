import hashlib
import hmac
import json
from datetime import timedelta

from django.utils import timezone
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
from rest_framework import status
from common.master_view import BaseModelViewSet
from common.models import FinancialYearModel
from subscription.models import FeatureUsage
from subscription.serializers_new import (
    PaymentSubscriptionSerializer,
    SubscriptionAPISerializer,
    SubscriptionCreateSerializer,
    SubscriptionInvoiceSerializer,
    SubscriptionSerializer,
    UserSubscriptionMeSerializer,
    UserSubscriptionSerializer,
)
from subscription.services.pricing import calculate_price

from .models import (
    PaymentSubscription,
    PlanPrice,
    PromoCode,
    Subscription,
    SubscriptionInvoice,
    UserSubscription,
)


def _complete_payment(payment, razorpay_payment_id, payment_method=None, amount=None):
    """Mark a verified payment paid and provision its subscription once."""
    with transaction.atomic():
        payment = PaymentSubscription.objects.select_for_update().select_related(
            "plan_price"
        ).get(pk=payment.pk)

        if payment.status == "paid":
            return payment, False

        if not payment.plan_price:
            raise ValueError("No plan price associated with payment")

        payment.status = "paid"
        payment.payment_date = now()
        payment.razorpay_payment_id = razorpay_payment_id
        if payment_method:
            payment.payment_method = payment_method
        if amount is not None:
            payment.amount = amount
        payment.save()

        current_date = now().date()
        duration = payment.plan_price.duration_days
        user_sub, created = UserSubscription.objects.get_or_create(
            user=payment.user,
            plan_price=payment.plan_price,
            defaults={
                "start_date": current_date,
                "end_date": current_date + timedelta(days=duration),
                "is_active": True,
            },
        )

        if not created:
            user_sub.end_date = max(user_sub.end_date, current_date) + timedelta(
                days=duration
            )
            user_sub.is_active = True
            user_sub.save(update_fields=["end_date", "is_active", "updated_at"])

        FeatureUsage.objects.filter(user=payment.user).update(used=0)
        return payment, True


class SubscriptionViewSet(BaseModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionAPISerializer
    list_serializer_class = SubscriptionAPISerializer
    response_serializer_class = SubscriptionAPISerializer

    create_message = "Subscription Created Successfully"
    update_message = "Subscription Updated Successfully"

    searching_fields = BaseModelViewSet.searching_fields + [
        "package_name",
        "description",
    ]
    ordering_fields = [
        "package_name",
        "no_of_profile_assessment",
        "no_of_tokens",
        "internship_access_type",
        "no_of_internship_access",
        "job_portal_access_type",
        "no_of_job_portal_access",
        "course_portal_access_type",
        "no_of_course_portal_access",
        "project_topic_access_type",
        "no_of_project_topic_access",
        "career_compare",
        "career_roadmap",
        "ai_chat_access",
    ]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return SubscriptionCreateSerializer
        return SubscriptionAPISerializer

    @action(detail=True, methods=["patch"], url_path="restore")
    def restore(self, request, pk=None):
        subscription = Subscription.objects.filter(pk=pk, deleted=True).first()

        if not subscription:
            return Response(
                {
                    "success": False,
                    "message": "Subscription not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        subscription.deleted = False
        subscription.deleted_at = None

        if hasattr(subscription, "deleted_by"):
            subscription.deleted_by = None

        subscription.updated_by = request.user
        subscription.updated_at = timezone.now()
        subscription.save()
        response_serializer = self.get_response_serializer(subscription)
        return Response(
            {
                "success": True,
                "message": "Subscription restored successfully",
                "data": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# class SubscriptionViewSet(ModelViewSet):
#     queryset = Subscription.objects.filter(deleted=False)
#     serializer_class = SubscriptionAPISerializer

#     def get_serializer_class(self):
#         if self.action in ("create", "update", "partial_update"):
#             return SubscriptionCreateSerializer
#         return SubscriptionAPISerializer

#     def create(self, request, *args, **kwargs):
#         # Validate with create serializer, respond with clean API serializer
#         create_ser = SubscriptionCreateSerializer(
#             data=request.data, context={"request": request}
#         )
#         create_ser.is_valid(raise_exception=True)
#         instance = create_ser.save()
#         resp_ser = SubscriptionAPISerializer(instance)
#         return Response(
#             {
#                 "success": True,
#                 "message": "Subscription package created successfully",
#                 "data": resp_ser.data,
#             },
#             status=201,
#         )

#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         create_ser = SubscriptionCreateSerializer(
#             instance, data=request.data, context={"request": request}
#         )
#         create_ser.is_valid(raise_exception=True)
#         instance = create_ser.save()
#         resp_ser = SubscriptionAPISerializer(instance)
#         return Response(
#             {
#                 "success": True,
#                 "message": "Subscription package updated successfully",
#                 "data": resp_ser.data,
#             },
#         )

#     def partial_update(self, request, *args, **kwargs):
#         instance = self.get_object()
#         create_ser = SubscriptionCreateSerializer(
#             instance, data=request.data, partial=True, context={"request": request}
#         )
#         create_ser.is_valid(raise_exception=True)
#         instance = create_ser.save()
#         resp_ser = SubscriptionAPISerializer(instance)
#         return Response(
#             {
#                 "success": True,
#                 "message": "Subscription package updated successfully",
#                 "data": resp_ser.data,
#             },
#         )

#     def perform_destroy(self, instance):
#         """Soft-delete: mark as deleted instead of removing from DB."""
#         instance.deleted = True
#         instance.deleted_at = now()
#         if self.request.user.is_authenticated:
#             instance.deleted_by = self.request.user
#         instance.save()


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
        user_sub = (
            UserSubscription.objects.filter(user=request.user, is_active=True)
            .select_related("plan_price__plan")
            .first()
        )
        if not user_sub:
            return Response({"subscription": None})

        # Ensure monthly usage counts are up-to-date before responding
        from utils.token_check import _reset_subscription_monthly_tokens

        _reset_subscription_monthly_tokens(request.user, user_sub)

        serializer = UserSubscriptionMeSerializer(
            user_sub, context={"request": request}
        )
        return Response(serializer.data)


class PaymentSubscriptionViewSet(ModelViewSet):
    queryset = PaymentSubscription.objects.all()
    serializer_class = PaymentSubscriptionSerializer
    client = razorpay.Client(
        auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_SECRET"))
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        # create pending payment (acts like cart)
        serializer.save(user=self.request.user, status="pending")

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        payment = self.get_object()

        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_signature = request.data.get("razorpay_signature")
        if not all((razorpay_payment_id, razorpay_order_id, razorpay_signature)):
            return Response(
                {"detail": "razorpay_payment_id, razorpay_order_id and razorpay_signature are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.user_id != request.user.id:
            return Response({"detail": "Payment does not belong to this user"}, status=403)
        if payment.razorpay_order_id != razorpay_order_id:
            return Response({"detail": "Order does not match payment"}, status=400)

        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
                }
            )
        except Exception:
            return Response({"detail": "Invalid Razorpay payment signature"}, status=400)

        try:
            payment, completed = _complete_payment(
                payment,
                razorpay_payment_id,
                request.data.get("payment_method"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(
            {"detail": "Payment successful", "already_completed": not completed},
            status=status.HTTP_200_OK,
        )

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

        plan_price = None
        if plan_price_id:
            plan_price = PlanPrice.objects.filter(
                id=plan_price_id, is_active=True, deleted=False, plan__deleted=False
            ).first()
            if not plan_price:
                return Response(
                    {"success": False, "message": "Invalid plan_price_id"}, status=400
                )
        elif subscription_id:
            subscription = Subscription.objects.filter(
                id=subscription_id, deleted=False
            ).first()
            if not subscription:
                return Response(
                    {"success": False, "message": "Invalid subscription"}, status=400
                )
            plan_price = (
                PlanPrice.objects.filter(
                    plan=subscription, is_active=True, deleted=False
                )
                .order_by("-price")
                .first()
            )
            if not plan_price:
                return Response(
                    {"success": False, "message": "No active prices for subscription"},
                    status=400,
                )

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

        # generate invoice number here (use FinancialYearModel)
        get_current_year = FinancialYearModel.get_current_financial_year()
        if not get_current_year:
            return Response(
                {
                    "success": False,
                    "message": "No active financial year found",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
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
    if not webhook_secret or not received_signature:
        return HttpResponse(status=400)

    # Verify signature
    expected_signature = hmac.new(
        bytes(webhook_secret, "utf-8"), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        return HttpResponse(status=400)

    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return HttpResponse(status=400)

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

        try:
            _complete_payment(
                payment,
                razorpay_payment_id,
                payment_method=method,
                amount=amount,
            )
        except ValueError:
            return HttpResponse(status=400)

    return HttpResponse(status=200)
