import razorpay
from decouple import config
from django.utils.timezone import now, timedelta
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from activity_log.models import ActivityLog
from company.models import Company
from subscription.models import (
    PaymentSubscription,
    PurchasedSubscription,
    StripeCharge,
    Subcription,
    SubscriptionInvoice,
)
from subscription.serializer import (
    PaymentSubscriptionSerializer,
    PurchasedSubscriptionSerializer,
    StripeChargeSerializer,
    SubcriptionDeleteSerializer,
    SubcriptionGetSerializer,
    SubcriptionRestoreSerializer,
    SubcriptionSerializer,
    SubcriptionStatusSerializer,
    SubscriptionInvoiceDeleteSerializer,
    SubscriptionInvoiceRestoreSerializer,
    SubscriptionInvoiceSerializer,
)
from utils.generate_ip_address import get_client_ip
from utils.pagination import Pagination

RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID")
RAZORPAY_SECRET = config("RAZORPAY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_SECRET))


class StripeChargeViewSet(ModelViewSet):
    queryset = StripeCharge.objects.filter(deleted=0).order_by("-id")
    serializer_class = StripeChargeSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "stripe_id",
        "amount",
        "currency",
        "description",
        "status",
        "paid",
        "captured",
        "payment_method",
        "company",
        "invoice_no",
        "fiscal_year",
        "created_by",
        "updated_by",
    ]

    ordering_fields = [
        "stripe_id",
        "amount",
        "currency",
        "description",
        "status",
        "paid",
        "captured",
        "payment_method",
        "company",
        "invoice_no",
        "fiscal_year",
        "created_by",
        "updated_by",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Stripe Charge Deleted"},
            status=status.HTTP_200_OK,
        )


class SubcriptionViewSet(ModelViewSet):
    queryset = Subcription.objects.filter(deleted=0).order_by("-id")
    serializer_class = SubcriptionSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    ordering_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = SubcriptionGetSerializer(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubcriptionGetSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = SubcriptionGetSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        serializer = SubcriptionSerializer(data=data)

        if serializer.is_valid():
            instance = serializer.save()
            serializer = SubcriptionGetSerializer(instance)

            ip_address = get_client_ip(request)
            ActivityLog.log.subcription_create(instance, ip_address, request.user)

            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = SubcriptionGetSerializer(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()
            serializer = SubcriptionGetSerializer(instance)
            ActivityLog.log.subcription_update(instance, request.user)

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "Subcription Deleted"},
            status=status.HTTP_200_OK,
        )

    @action(methods=["patch"], detail=True, url_path="subscription-status")
    def subscription_status_update(self, request, pk):
        data = request.data
        instance = self.get_object()
        serializer = SubcriptionStatusSerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            subscription = serializer.save()
            if subscription.status == "active":
                return Response(
                    {"success": True, "message": "Subscription is activated"},
                    status=status.HTTP_200_OK,
                )
            else:
                subscription.status == "in_active"
                return Response(
                    {"success": True, "message": "Subscription is deactivated"},
                    status=status.HTTP_200_OK,
                )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Subscription Delete
class SubcriptionDeleteViewSet(ModelViewSet):
    queryset = Subcription.objects.filter(deleted=0).order_by("-id")
    serializer_class = SubcriptionGetSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    ordering_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    def create(self, request, *args, **kwargs):
        serializer = SubcriptionDeleteSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            ActivityLog.log.subcription_archive(instance, request.user)

            return Response(
                {"success": True, "message": "Subscription Archive Success"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Subscription Restore
class SubcriptionRestoreViewSet(ModelViewSet):
    queryset = Subcription.objects.filter(deleted=1).order_by("-id")
    serializer_class = SubcriptionGetSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    ordering_fields = [
        "package_name",
        "subscription_type",
        "per_user_price",
        "discount",
        "sell_price",
        "duration",
        "description",
        "subscriptionfeature__feature_name",
        "subscriptionfeature__feature_status",
    ]

    def create(self, request, *args, **kwargs):
        serializer = SubcriptionRestoreSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            ActivityLog.log.subcription_restore(instance, request.user)

            return Response(
                {"success": True, "message": "Subscription Restore Success"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Subscription Inovice
class SubscriptionInvoiceViewSet(ModelViewSet):
    queryset = SubscriptionInvoice.objects.filter(deleted=0).order_by("-id")
    serializer_class = SubscriptionInvoiceSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]
    ordering_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]

    def create(self, request, *args, **kwargs):
        data = request.data
        data["created_by"] = request.user.id
        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            return Response(
                {"success": True, "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.serializer_class(instance)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        data = request.data
        data["updated_by"] = request.user.id
        instance = self.get_object()
        serializer = self.serializer_class(instance, data=data, partial=True)

        if serializer.is_valid():
            instance = serializer.save()
            ActivityLog.log.performa_invoice_update(instance, request.user)

            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"success": False, "message": False}, status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = 1
        instance.save()
        return Response(
            {"success": True, "message": "performa_invoice Deleted"},
            status=status.HTTP_200_OK,
        )


# Subscription Invoice Delete
class SubscriptionInvoiceDeleteViewSet(ModelViewSet):
    queryset = SubscriptionInvoice.objects.filter(deleted=0).order_by("-id")
    serializer_class = SubscriptionInvoiceSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]
    ordering_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]

    def create(self, request, *args, **kwargs):
        serializer = SubscriptionInvoiceDeleteSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {"success": True, "message": "Performa Invoice Archive Success"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Subscription Invoice Restore
class SubscriptionInvoiceRestoreViewSet(ModelViewSet):
    queryset = SubscriptionInvoice.objects.filter(deleted=1).order_by("-id")
    serializer_class = SubscriptionInvoiceSerializer
    pagination_class = Pagination
    filter_backends = [SearchFilter, OrderingFilter]
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    search_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]
    ordering_fields = [
        "invoice_number",
        "invoice_date",
        "due_date",
        "company",
        "currency",
        "subscription",
        "quantity",
        "sell_price",
        "gst_rate",
        "amount",
        "note",
        "cgst",
        "sgst",
        "total",
        "payment_reference_id",
        "check_out_url",
        "active",
    ]

    def create(self, request, *args, **kwargs):
        serializer = SubscriptionInvoiceRestoreSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "success": True,
                    "message": "Performa Invoice Restore Successfully",
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Subscription Invoice Archive
class SubscriptionInvoiceArchiveViewSet(ModelViewSet):
    queryset = SubscriptionInvoice.objects.filter(deleted=0).order_by("-id")
    serializer_class = SubscriptionInvoiceDeleteSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    pagination_class = Pagination

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SubscriptionInvoiceSerializer(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = SubscriptionInvoiceSerializer(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = SubscriptionInvoiceDeleteSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Subscription Archive Successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": True, "message": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PurchasedSubscriptionViewSet(ModelViewSet):
    queryset = PurchasedSubscription.objects.filter(deleted=0).order_by("-id")
    serializer_class = PurchasedSubscriptionSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class PaymentSubscriptionViewSet(ModelViewSet):
    queryset = PaymentSubscription.objects.all()
    serializer_class = PaymentSubscriptionSerializer
    pagination_class = Pagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def list(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")

        queryset = self.filter_queryset(self.get_queryset())

        # Filter by company_id if provided
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        no_pagination = request.query_params.get("no_pagination")
        if no_pagination:
            serializer = self.serializer_class(queryset, many=True)
            return Response({"success": True, "data": serializer.data})

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return self.get_paginated_response(
                {"success": True, "data": serializer.data}
            )

        serializer = self.serializer_class(queryset, many=True)
        return self.get_paginated_response({"success": True, "data": serializer.data})

    def create(self, request, *args, **kwargs):
        company_id = request.data.get("company")
        subscription_id = request.data.get("subscription")
        currency = request.data.get("currency")

        company = Company.objects.get(id=company_id)
        subscription = Subcription.objects.get(id=subscription_id)

        base_price = subscription.sell_price
        gst_amount = base_price * 0.18
        sell_price = base_price + gst_amount

        duration = int(subscription.duration)  # type: ignore
        start_date = now().date()
        end_date = start_date + timedelta(days=duration)

        # Create payment link
        payment_link_data = {
            "amount": int(sell_price * 100),
            "currency": currency,
            "accept_partial": False,
            "description": f"Subscription Payment for {subscription.package_name}",
            "customer": {
                "name": company.name,
                "contact": company.phone,
                "email": company.email,
            },
            "notify": {"sms": True, "email": True},
            "reminder_enable": True,
            "callback_url": "http://localhost:3000/payment-subscription/",
            "callback_method": "get",
        }

        razorpay_payment_link = client.payment_link.create(  # type: ignore
            payment_link_data
        )

        razor_payment_link_id = razorpay_payment_link["id"]

        subscription_entry = PaymentSubscription.objects.create(
            company=company,
            subscription=subscription,
            sell_price=sell_price,
            amount=0.0,
            duration=duration,
            start_date=start_date,
            end_date=end_date,
            check_out_url=razorpay_payment_link["short_url"],
            invoice_no="0",
            active="inactive",
            status="Pending",
            razor_order_id=razor_payment_link_id,
            payment_id="",
            currency=currency,
        )

        serializer = PaymentSubscriptionSerializer(subscription_entry)
        return Response(
            {
                "status": True,
                "message": "Subscription Created",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["PATCH"],
        url_path="update-payment-data",
        permission_classes=[],
    )
    def update_payment_data(self, request):
        try:
            razor_payment_id = request.data.get("razorpay_payment_id")
            razor_payment_link_id = request.data.get("razorpay_payment_link_id")
            razor_payment_link_status = request.data.get("razorpay_payment_link_status")

            if not razor_payment_link_id:
                return Response(
                    {"status": False, "message": "No payment link ID provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                existing_subscriptions = PaymentSubscription.objects.filter(
                    razor_order_id=razor_payment_link_id
                )

                if not existing_subscriptions.exists():
                    return Response(
                        {"status": False, "message": "No matching subscription found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

                payment_subscription = existing_subscriptions.first()

            except Exception as e:
                return Response(
                    {"status": False, "message": f"Database error: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            if razor_payment_link_status != "paid":
                return Response(
                    {"status": False, "message": "Payment not completed yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if razor_payment_id:
                try:
                    payment_details = client.payment.fetch(  # type: ignore
                        razor_payment_id
                    )
                    actual_amount_paid = payment_details["amount"] / 100
                    payment_subscription.amount = actual_amount_paid  # type: ignore
                except Exception as e:
                    payment_subscription.amount = (  # type: ignore
                        payment_subscription.sell_price  # type: ignore
                    )
                    print(f"Error fetching payment details: {str(e)}")
            else:
                payment_subscription.amount = (  # type: ignore
                    payment_subscription.sell_price  # type: ignore
                )

            serializer = PaymentSubscriptionSerializer(payment_subscription)
            return Response(
                {
                    "status": True,
                    "message": "Payment data updated successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": f"Error updating payment data: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["GET"], url_path="download-invoice")
    def download_invoice(self, request, pk=None):
        try:
            company_id = request.query_params.get("company_id")
            if not company_id:
                return Response(
                    {"success": False, "error": "Company ID is required"}, status=400
                )

            subscription = PaymentSubscription.objects.filter(
                pk=pk, company_id=company_id
            ).first()
            if not subscription:
                return Response(
                    {
                        "success": False,
                        "error": "Subscription not found for this company",
                    },
                    status=404,
                )

            from_data = {
                "name": "IKSHANA AUTOMATION PRIVATE LIMITED",
                "address": (
                    "701, 7TH FLOOR, SUN AVENUE ONE, NEAR SUN PRIMA, Ambawadi, "
                    "Ahmedabad, Gujarat, 380006"
                ),
                "email": "support@ikshanaautomation.com",
                "phone": "+91 9714174440",
                "gst_no": "24AAHCI9193A1ZL",
                "logo": request.build_absolute_uri("/static/images/procemlogo.png"),
            }

            to_company = subscription.company
            to_data = {
                "name": to_company.name,
                "address": (
                    f"{to_company.registered_business_address_building}, "
                    f"{to_company.registered_business_address_area}, "
                    f"{to_company.registered_business_address_landmark}, "
                    f"{to_company.registered_business_address_state}, "
                    f"{to_company.registered_business_address_city}, "
                    f"{to_company.registered_business_address_pincode}"
                ),
                "email": to_company.email,
                "phone": to_company.phone,
                "gst_no": to_company.gst_no if hasattr(to_company, "gst_no") else "N/A",
            }

            # GST Calculation (CGST 9% + SGST 9%)
            base_price = subscription.subscription.sell_price
            cgst = base_price * 0.09
            sgst = base_price * 0.09
            total_price = base_price + cgst + sgst

            invoice_data = {
                "subscription_name": subscription.subscription.package_name,
                "rate": subscription.subscription.per_user_price,
                "discount": subscription.subscription.discount,
                "amount": base_price,
                "cgst": round(cgst, 2),
                "sgst": round(sgst, 2),
                "total_amount": round(total_price, 2),
            }

            bank_details = {
                "company_name": "Nivzen Online Deals LLP",
                "pan": "AATFN3023G",
                "account_no": "025905004907",
                "bank_name": "ICICI Bank, S.G. Highway Ahmedabad (Gujarat) India",
                "ifsc_code": "ICIC0002895",
                "swift_code": "ICICINBBCTS",
            }

            response_data = {
                "success": True,
                "data": {
                    "from": from_data,
                    "to": to_data,
                    "invoice_no": subscription.invoice_no,
                    "date": subscription.start_date.strftime("%d-%m-%y"),
                    "invoice_data": invoice_data,
                    "bank_details": bank_details,
                },
            }

            return Response(response_data, status=200)

        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)
