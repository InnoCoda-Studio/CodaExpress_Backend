from decimal import Decimal
import random
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Order,
    OrderMessage,
    RiderWallet,
    WalletTransaction,
    settle_completed_order_commission,
)
from .serializers import OrderSerializer, OrderMessageSerializer


class CreateOrderView(generics.CreateAPIView):
    """Customer endpoint to book a new delivery run with vehicle tier"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        pin = f"{random.randint(1000, 9999)}"
        serializer.save(
            customer=self.request.user,
            status=Order.Status.PENDING,
            dropoff_pin=pin,
        )


class CustomerOrderListView(generics.ListAPIView):
    """Customer endpoint to view all their booked deliveries"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by("-created_at")


class AvailableOrdersListView(generics.ListAPIView):
    """Rider endpoint: filters pending orders based on rider vehicle type"""

    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        rider_vehicle = Order.VehicleRequirement.MOTORCYCLE
        if hasattr(user, "rider_profile") and user.rider_profile:
            rider_vehicle = user.rider_profile.vehicle_type

        queryset = Order.objects.filter(status=Order.Status.PENDING)

        if rider_vehicle == Order.VehicleRequirement.BICYCLE:
            queryset = queryset.filter(required_vehicle=Order.VehicleRequirement.BICYCLE)
        elif rider_vehicle == Order.VehicleRequirement.MOTORCYCLE:
            queryset = queryset.filter(
                required_vehicle__in=[
                    Order.VehicleRequirement.BICYCLE,
                    Order.VehicleRequirement.MOTORCYCLE,
                ]
            )

        return queryset.order_by("-created_at")


class AcceptOrderView(APIView):
    """Rider endpoint to claim an order with minimum wallet float guardrail"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(pk=pk)
            except Order.DoesNotExist:
                return Response(
                    {"error": "Order not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            wallet, _ = RiderWallet.objects.select_for_update().get_or_create(
                rider=request.user
            )

            if wallet.is_frozen:
                return Response(
                    {"error": "Your rider wallet is frozen. Please contact support."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if wallet.balance < wallet.minimum_float:
                return Response(
                    {
                        "error": (
                            f"Insufficient wallet float. Maintain at least "
                            f"₦{wallet.minimum_float:,.2f} to accept orders."
                        ),
                        "code": "INSUFFICIENT_WALLET_FLOAT",
                        "balance": str(wallet.balance),
                        "minimum_float": str(wallet.minimum_float),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if order.status != Order.Status.PENDING or order.rider_id is not None:
                return Response(
                    {"error": "Order has already been taken or cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.rider = request.user
            order.status = Order.Status.ACCEPTED
            order.accepted_at = timezone.now()
            order.save(update_fields=["rider", "status", "accepted_at"])

        return Response(
            {
                "message": "Order accepted successfully!",
                "order": OrderSerializer(order).data,
            }
        )


class UpdateOrderStatusView(APIView):
    """Endpoint for polling order status (GET) and rider progress updates (PATCH)"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.select_related("rider", "customer").get(pk=pk)
            if (
                order.customer != request.user
                and order.rider != request.user
                and not request.user.is_staff
            ):
                return Response(
                    {"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN
                )

            rider_data = None
            if order.rider:
                rp = getattr(order.rider, "rider_profile", None)
                rider_data = {
                    "full_name": order.rider.get_full_name() or order.rider.username,
                    "phone_number": getattr(order.rider, "phone_number", "") or "",
                    "rating": str(getattr(rp, "rating", "5.0")) if rp else "5.0",
                    "total_trips": getattr(rp, "completed_trips", 0) if rp else 0,
                    "vehicle_type": getattr(rp, "vehicle_type", "") if rp else "",
                    "vehicle_model": (
                        " ".join(
                            filter(
                                None,
                                [
                                    getattr(rp, "vehicle_make", ""),
                                    getattr(rp, "vehicle_model", ""),
                                ],
                            )
                        )
                        if rp
                        else ""
                    ),
                    "plate_number": getattr(rp, "plate_number", "") if rp else "",
                }

            return Response(
                {
                    "status": order.status,
                    "order": OrderSerializer(order).data,
                    "rider": rider_data,
                }
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, pk):
        new_status = request.data.get("status")
        entered_pin = request.data.get("dropoff_pin")

        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(
                    pk=pk, rider=request.user
                )
            except Order.DoesNotExist:
                return Response(
                    {"error": "Order not found or unauthorized."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if new_status == Order.Status.IN_TRANSIT:
                order.status = Order.Status.IN_TRANSIT
                order.in_transit_at = timezone.now()
                order.save(update_fields=["status", "in_transit_at"])
                return Response(
                    {
                        "message": "Order is now in transit.",
                        "order": OrderSerializer(order).data,
                    }
                )

            if new_status == Order.Status.ARRIVED_DROPOFF:
                order.status = Order.Status.ARRIVED_DROPOFF
                order.arrived_at_dropoff_at = timezone.now()
                order.save(update_fields=["status", "arrived_at_dropoff_at"])
                return Response(
                    {
                        "message": "Arrival logged at drop-off. 5-minute grace period active.",
                        "order": OrderSerializer(order).data,
                    }
                )

            if new_status == Order.Status.COMPLETED:
                valid_pin = bool(
                    order.dropoff_pin
                    and entered_pin
                    and str(entered_pin).strip() == str(order.dropoff_pin).strip()
                )
                if not valid_pin:
                    return Response(
                        {"error": "Invalid 4-digit drop-off PIN."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if order.status != Order.Status.COMPLETED:
                    order.completed_at = timezone.now()
                    if order.final_earnings is None:
                        order.final_earnings = Decimal(str(order.dynamic_earnings))
                    order.status = Order.Status.COMPLETED
                    order.save(
                        update_fields=["status", "completed_at", "final_earnings"]
                    )

                commission_txn = settle_completed_order_commission(order)
                wallet = RiderWallet.objects.filter(rider=request.user).first()
                commission = (
                    commission_txn.amount if commission_txn else Decimal("0.00")
                )

                return Response(
                    {
                        "message": "Delivery completed successfully!",
                        "final_payout": f"₦{order.final_earnings:,.0f}",
                        "commission_deducted": f"₦{commission}",
                        "new_wallet_balance": (
                            f"₦{wallet.balance:,.2f}" if wallet else "₦0.00"
                        ),
                        "order": OrderSerializer(order).data,
                    }
                )

            return Response(
                {"error": "Invalid status transition."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateOrderFareView(APIView):
    """Customer endpoint to dynamically adjust offered fare while searching"""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, customer=request.user)
            if order.status != Order.Status.PENDING:
                return Response(
                    {"error": "Cannot change fare after a rider has accepted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_fare = request.data.get("base_earnings") or request.data.get("fare")
            if new_fare is None or Decimal(str(new_fare)) < Decimal("500"):
                return Response(
                    {"error": "Invalid fare amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            order.base_earnings = Decimal(str(new_fare))
            order.save(update_fields=["base_earnings"])
            return Response(
                {
                    "message": "Fare updated successfully.",
                    "order": OrderSerializer(order).data,
                }
            )
        except Order.DoesNotExist:
            return Response(
                {"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND
            )


class OrderMessageListCreateView(generics.ListCreateAPIView):
    """Fetch messages or send a new message for a specific order"""

    serializer_class = OrderMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OrderMessage.objects.filter(order_id=self.kwargs["order_id"])

    def perform_create(self, serializer):
        order = Order.objects.get(pk=self.kwargs["order_id"])
        serializer.save(sender=self.request.user, order=order)