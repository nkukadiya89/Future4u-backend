import datetime
from types import SimpleNamespace

from django.db import transaction
from django.utils.timezone import now
from rest_framework import serializers, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from subscription.models import (
    PaymentSubscription,
    PaymentSubscriptionItem,
    Subscription,
    SubscriptionCart,
)


class SubscriptionAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = "__all__"


class PaymentSubscriptionAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSubscription
        fields = "__all__"


class _RazorpayClientStub:
    payment_link = SimpleNamespace(
        create=lambda *_a, **_k: (_ for _ in ()).throw(
            RuntimeError("Razorpay not configured")
        )
    )
    payment = SimpleNamespace(
        fetch=lambda *_a, **_k: (_ for _ in ()).throw(
            RuntimeError("Razorpay not configured")
        )
    )


try:  # pragma: no cover
    import razorpay  # type: ignore
    from decouple import config  # type: ignore

    client = razorpay.Client(
        auth=(
            config("RAZORPAY_KEY_ID", default=""),
            config("RAZORPAY_KEY_SECRET", default=""),
        )
    )
except Exception:  # pragma: no cover
    client = _RazorpayClientStub()


class SubscriptionViewSet(ModelViewSet):
    queryset = Subscription.objects.filter(deleted=False).order_by("-id")
    serializer_class = SubscriptionAPISerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        ser = self.get_serializer(qs, many=True)
        return Response({"success": True, "data": ser.data})

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        ser = self.get_serializer(obj)
        return Response({"success": True, "data": ser.data})

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser.save(created_by=request.user, updated_by=request.user)
        return Response(
            {"success": True, "data": ser.data}, status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        obj = self.get_object()
        ser = self.get_serializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return Response(
                {"success": False, "message": ser.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser.save(updated_by=request.user)
        return Response({"success": True, "data": ser.data})

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.deleted = True
        obj.deleted_at = now()
        obj.deleted_by = request.user
        obj.save(update_fields=["deleted", "deleted_at", "deleted_by"])
        return Response(
            {"success": True, "message": "Deleted"}, status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["patch"], url_path="subscription-status")
    def subscription_status(self, request, pk=None, *args, **kwargs):
        obj = self.get_object()
        new_status = request.data.get("status")
        if new_status not in ("active", "in_active"):
            return Response(
                {"success": False, "message": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj.status = new_status
        obj.updated_by = request.user
        obj.updated_at = now()
        obj.save(update_fields=["status", "updated_by", "updated_at"])
        ser = self.get_serializer(obj)
        return Response({"success": True, "data": ser.data}, status=200)


class PaymentSubscriptionViewSet(ModelViewSet):
    queryset = PaymentSubscription.objects.all().order_by("-id")
    serializer_class = PaymentSubscriptionAPISerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        company_id = request.query_params.get("company_id")
        if company_id not in (None, ""):
            qs = qs.filter(company_id=company_id)
        ser = self.get_serializer(qs, many=True)
        return Response({"success": True, "data": ser.data})

    @action(detail=False, methods=["patch"], url_path="update-payment-data")
    def update_payment_data(self, request, *args, **kwargs):
        link_id = request.data.get("razorpay_payment_link_id")
        link_status = request.data.get("razorpay_payment_link_status")
        payment_id = request.data.get("razorpay_payment_id")

        if not link_id:
            return Response(
                {"status": False, "message": "No payment link ID provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ps = (
            PaymentSubscription.objects.filter(razor_order_id=link_id)
            .order_by("-id")
            .first()
        )
        if not ps:
            return Response(
                {"status": False, "message": "No matching subscription found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if link_status != "paid":
            return Response(
                {"status": False, "message": "Payment not completed yet"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # optional verification
        if payment_id:
            try:
                payment_details = client.payment.fetch(payment_id)
                amt = float(payment_details.get("amount", 0)) / 100.0
                if amt:
                    ps.amount = amt
            except Exception:
                ps.amount = ps.total_amount
        else:
            ps.amount = ps.total_amount

        ps.payment_id = payment_id
        ps.payment_status = "paid"
        ps.active = "Active"
        if not ps.invoice_no or ps.invoice_no == "0":
            ps.invoice_no = (
                ps.invoice_no
                if ps.invoice_no not in (None, "", "0")
                else (payment_id or f"inv_{ps.id}")
            )
        ps.payment_date = now()
        ps.save()

        # Ensure items have dates
        start_date = now().date()
        for item in ps.items.all():
            end_date = None
            raw = (item.subscription_type or "").lower()
            if "year" in raw:
                n = int(raw.split("year")[0].strip() or "1")
                end_date = start_date + datetime.timedelta(days=365 * n)
            elif "month" in raw:
                n = int(raw.split("month")[0].strip() or "1")
                end_date = start_date + datetime.timedelta(days=30 * n)
            elif "day" in raw:
                n = int(raw.split("day")[0].strip() or "1")
                end_date = start_date + datetime.timedelta(days=n)
            item.start_date = item.start_date or start_date
            item.end_date = item.end_date or end_date
            item.save(update_fields=["start_date", "end_date"])

        ser = self.get_serializer(ps)
        return Response({"status": True, "data": ser.data}, status=status.HTTP_200_OK)


def _require_company(request):
    company = getattr(request.user, "company", None)
    if not company:
        return None, Response(
            {"success": False, "message": "User is not associated with a company"},
            status=400,
        )
    return company, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cart_add_to_cart(request):
    company, err = _require_company(request)
    if err:
        return err
    company_id = request.data.get("company")
    sub_id = request.data.get("subscription")
    qty = int(request.data.get("quantity") or 1)
    if str(company_id) != str(company.id):
        return Response({"success": False, "message": "Invalid company"}, status=400)
    row, _ = SubscriptionCart.objects.get_or_create(
        company_id=company_id, subscription_id=sub_id, defaults={"quantity": 0}
    )
    row.quantity = max(1, row.quantity + qty)
    row.save()
    return Response({"success": True, "data": {"id": row.id}}, status=201)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cart_items(request):
    company, err = _require_company(request)
    if err:
        return err
    qs = (
        SubscriptionCart.objects.filter(company=company, deleted=False)
        .select_related("subscription")
        .order_by("id")
    )
    out = []
    for row in qs:
        out.append(
            {
                "id": row.id,
                "company": row.company_id,
                "subscription": row.subscription_id,
                "device_quantity": row.quantity,
                "subscription_price": (
                    row.subscription.subscription_sell_price if row.subscription else 0
                ),
            }
        )
    return Response({"success": True, "data": out}, status=200)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cart_increment(request):
    company, err = _require_company(request)
    if err:
        return err
    company_id = request.data.get("company")
    sub_id = request.data.get("subscription")
    row = SubscriptionCart.objects.filter(
        company_id=company_id, subscription_id=sub_id, deleted=False
    ).first()
    if not row:
        return Response({"success": False, "message": "Not found"}, status=404)
    row.quantity += 1
    row.save()
    return Response({"success": True}, status=200)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def cart_decrement(request):
    company, err = _require_company(request)
    if err:
        return err
    company_id = request.data.get("company")
    sub_id = request.data.get("subscription")
    row = SubscriptionCart.objects.filter(
        company_id=company_id, subscription_id=sub_id, deleted=False
    ).first()
    if not row:
        return Response({"success": False, "message": "Not found"}, status=404)
    row.quantity = max(1, row.quantity - 1)
    row.save()
    return Response({"success": True}, status=200)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cart_remove(request, pk: int):
    row = SubscriptionCart.objects.filter(pk=pk, deleted=False).first()
    if not row:
        return Response({"success": False, "message": "Not found"}, status=404)
    row.deleted = True
    row.save(update_fields=["deleted"])
    return Response({"success": True}, status=200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def cart_checkout(request):
    company, err = _require_company(request)
    if err:
        return err
    items = request.data.get("items")
    if not items:
        return Response({"success": False, "message": "items is required"}, status=400)

    total_amount = float(request.data.get("total_amount") or 0)
    subtotal = float(request.data.get("subtotal") or 0)
    cgst = float(request.data.get("cgst") or 0)
    sgst = float(request.data.get("sgst") or 0)

    ps = PaymentSubscription.objects.create(
        company=company,
        amount=0.0,
        check_out_url="",
        invoice_no="0",
        active="Inactive",
        payment_status="pending",
        razor_order_id="",
        currency="INR",
        subtotal=subtotal,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=float(request.data.get("igst") or 0),
        total_amount=total_amount,
    )

    for it in items:
        PaymentSubscriptionItem.objects.create(
            payment_subscription=ps,
            subscription_id=it.get("subscription"),
            quantity=int(it.get("quantity") or 1),
            subscription_type=str(it.get("subscription_type") or ""),
            device_price=float(it.get("device_price") or 0),
            subscription_price=float(it.get("subscription_price") or 0),
            plan_total=float(it.get("plan_total") or 0),
        )

    link = client.payment_link.create(
        {"amount": int(total_amount * 100), "currency": "INR"}
    )
    ps.razor_order_id = link["id"]
    ps.check_out_url = link["short_url"]
    ps.save(update_fields=["razor_order_id", "check_out_url"])

    return Response(
        {
            "success": True,
            "data": {
                "payment_link": link["short_url"],
                "razorpay_payment_link_id": link["id"],
                "summary": {"total_amount": total_amount},
            },
        },
        status=201,
    )
