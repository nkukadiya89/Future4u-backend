# import datetime
# from types import SimpleNamespace

# from django.db import transaction
# from django.utils.timezone import now
# from rest_framework import serializers, status
# from rest_framework.decorators import action, api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework.viewsets import ModelViewSet

# from subscription.models import (
#     PaymentSubscription,
#     Subscription,
# )


# class SubscriptionAPISerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Subscription
#         fields = "__all__"


# class PaymentSubscriptionAPISerializer(serializers.ModelSerializer):
#     class Meta:
#         model = PaymentSubscription
#         fields = "__all__"


# class _RazorpayClientStub:
#     payment_link = SimpleNamespace(
#         create=lambda *_a, **_k: (_ for _ in ()).throw(
#             RuntimeError("Razorpay not configured")
#         )
#     )
#     payment = SimpleNamespace(
#         fetch=lambda *_a, **_k: (_ for _ in ()).throw(
#             RuntimeError("Razorpay not configured")
#         )
#     )


# try:  # pragma: no cover
#     import razorpay  # type: ignore
#     from decouple import config  # type: ignore

#     client = razorpay.Client(
#         auth=(
#             config("RAZORPAY_KEY_ID", default=""),
#             config("RAZORPAY_KEY_SECRET", default=""),
#         )
#     )
# except Exception:  # pragma: no cover
#     client = _RazorpayClientStub()


# class SubscriptionViewSet(ModelViewSet):
#     queryset = Subscription.objects.filter(deleted=False).order_by("-id")
#     serializer_class = SubscriptionAPISerializer
#     permission_classes = [IsAuthenticated]

#     def list(self, request, *args, **kwargs):
#         qs = self.get_queryset()
#         ser = self.get_serializer(qs, many=True)
#         return Response({"success": True, "data": ser.data})

#     def retrieve(self, request, *args, **kwargs):
#         obj = self.get_object()
#         ser = self.get_serializer(obj)
#         return Response({"success": True, "data": ser.data})

#     def create(self, request, *args, **kwargs):
#         ser = self.get_serializer(data=request.data)
#         if not ser.is_valid():
#             return Response(
#                 {"success": False, "message": ser.errors},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         ser.save(created_by=request.user, updated_by=request.user)
#         return Response(
#             {"success": True, "data": ser.data}, status=status.HTTP_201_CREATED
#         )

#     def partial_update(self, request, *args, **kwargs):
#         obj = self.get_object()
#         ser = self.get_serializer(obj, data=request.data, partial=True)
#         if not ser.is_valid():
#             return Response(
#                 {"success": False, "message": ser.errors},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         ser.save(updated_by=request.user)
#         return Response({"success": True, "data": ser.data})

#     def destroy(self, request, *args, **kwargs):
#         obj = self.get_object()
#         obj.deleted = True
#         obj.deleted_at = now()
#         obj.deleted_by = request.user
#         obj.save(update_fields=["deleted", "deleted_at", "deleted_by"])
#         return Response(
#             {"success": True, "message": "Deleted"}, status=status.HTTP_200_OK
#         )

#     @action(detail=True, methods=["patch"], url_path="subscription-status")
#     def subscription_status(self, request, pk=None, *args, **kwargs):
#         obj = self.get_object()
#         new_status = request.data.get("status")
#         if new_status not in ("active", "in_active"):
#             return Response(
#                 {"success": False, "message": "Invalid status"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )
#         obj.status = new_status
#         obj.updated_by = request.user
#         obj.updated_at = now()
#         obj.save(update_fields=["status", "updated_by", "updated_at"])
#         ser = self.get_serializer(obj)
#         return Response({"success": True, "data": ser.data}, status=200)


# class PaymentSubscriptionViewSet(ModelViewSet):
#     queryset = PaymentSubscription.objects.all().order_by("-id")
#     serializer_class = PaymentSubscriptionAPISerializer
#     permission_classes = [IsAuthenticated]

#     def list(self, request, *args, **kwargs):
#         qs = self.get_queryset()
#         company_id = request.query_params.get("company_id")
#         if company_id not in (None, ""):
#             qs = qs.filter(company_id=company_id)
#         ser = self.get_serializer(qs, many=True)
#         return Response({"success": True, "data": ser.data})

#     @action(detail=False, methods=["patch"], url_path="update-payment-data")
#     def update_payment_data(self, request, *args, **kwargs):
#         link_id = request.data.get("razorpay_payment_link_id")
#         link_status = request.data.get("razorpay_payment_link_status")
#         payment_id = request.data.get("razorpay_payment_id")

#         if not link_id:
#             return Response(
#                 {"status": False, "message": "No payment link ID provided"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         ps = (
#             PaymentSubscription.objects.filter(razor_order_id=link_id)
#             .order_by("-id")
#             .first()
#         )
#         if not ps:
#             return Response(
#                 {"status": False, "message": "No matching subscription found"},
#                 status=status.HTTP_404_NOT_FOUND,
#             )

#         if link_status != "paid":
#             return Response(
#                 {"status": False, "message": "Payment not completed yet"},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # optional verification
#         if payment_id:
#             try:
#                 payment_details = client.payment.fetch(payment_id)
#                 amt = float(payment_details.get("amount", 0)) / 100.0
#                 if amt:
#                     ps.amount = amt
#             except Exception:
#                 ps.amount = ps.total_amount
#         else:
#             ps.amount = ps.total_amount

#         ps.payment_id = payment_id
#         ps.payment_status = "paid"
#         ps.active = "Active"
#         if not ps.invoice_no or ps.invoice_no == "0":
#             ps.invoice_no = (
#                 ps.invoice_no
#                 if ps.invoice_no not in (None, "", "0")
#                 else (payment_id or f"inv_{ps.id}")
#             )
#         ps.payment_date = now()
#         ps.save()

#         # Ensure items have dates
#         start_date = now().date()
#         for item in ps.items.all():
#             end_date = None
#             raw = (item.subscription_type or "").lower()
#             if "year" in raw:
#                 n = int(raw.split("year")[0].strip() or "1")
#                 end_date = start_date + datetime.timedelta(days=365 * n)
#             elif "month" in raw:
#                 n = int(raw.split("month")[0].strip() or "1")
#                 end_date = start_date + datetime.timedelta(days=30 * n)
#             elif "day" in raw:
#                 n = int(raw.split("day")[0].strip() or "1")
#                 end_date = start_date + datetime.timedelta(days=n)
#             item.start_date = item.start_date or start_date
#             item.end_date = item.end_date or end_date
#             item.save(update_fields=["start_date", "end_date"])

#         ser = self.get_serializer(ps)
#         return Response({"status": True, "data": ser.data}, status=status.HTTP_200_OK)


# def _require_company(request):
#     company = getattr(request.user, "company", None)
#     if not company:
#         return None, Response(
#             {"success": False, "message": "User is not associated with a company"},
#             status=400,
#         )
#     return company, None
