from decimal import Decimal
import random
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderMessage, RiderWallet
from .serializers import OrderSerializer, OrderMessageSerializer

class CreateOrderView(generics.CreateAPIView):
    """Customer endpoint to book a new delivery run with vehicle tier"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        pin = f"{random.randint(1000, 9999)}"
        serializer.save(customer=self.request.user, status='PENDING', dropoff_pin=pin)


class CustomerOrderListView(generics.ListAPIView):
    """Customer endpoint to view all their booked deliveries"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')


class AvailableOrdersListView(generics.ListAPIView):
    """Rider endpoint: filters pending orders based on rider vehicle type"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Get rider's vehicle type from RiderProfile (defaults to MOTORCYCLE)
        rider_vehicle = 'MOTORCYCLE'
        if hasattr(user, 'rider_profile') and user.rider_profile:
            rider_vehicle = user.rider_profile.vehicle_type

        queryset = Order.objects.filter(status='PENDING')

        # Lagos vehicle capability filtering rules:
        # - Bicycles see only BICYCLE orders
        # - Motorcycles see BICYCLE and MOTORCYCLE orders
        # - Cars see all vehicle tiers (BICYCLE, MOTORCYCLE, CAR)
        if rider_vehicle == 'BICYCLE':
            queryset = queryset.filter(required_vehicle='BICYCLE')
        elif rider_vehicle == 'MOTORCYCLE':
            queryset = queryset.filter(required_vehicle__in=['BICYCLE', 'MOTORCYCLE'])

        return queryset.order_by('-created_at')


class AcceptOrderView(APIView):
    """Rider endpoint to claim an order with ₦10 minimum wallet balance guardrail"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            wallet, created = RiderWallet.objects.get_or_create(rider=request.user)
            
            # RULE: Rider must have at least ₦10 in their wallet to accept orders
            if wallet.balance < Decimal('10.00'):
                return Response(
                    {"error": "Insufficient wallet balance. Minimum ₦10 required to accept orders. Please top up your Moniepoint account."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            order = Order.objects.get(pk=pk)
            if order.status != 'PENDING':
                return Response({"error": "Order has already been taken or cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            
            order.rider = request.user
            order.status = 'ACCEPTED'
            order.accepted_at = timezone.now()
            order.save()

            return Response({
                "message": "Order accepted successfully!", 
                "order": OrderSerializer(order).data
            })
        
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)


class UpdateOrderStatusView(APIView):
    """Endpoint for both polling order status (GET) and rider progress updates (PATCH)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Allow customer or rider to poll order status and assigned rider details"""
        try:
            # Allow the customer who created it OR the assigned rider to view status
            order = Order.objects.get(pk=pk)
            if order.customer != request.user and order.rider != request.user and not request.user.is_staff:
                return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)

            rider_data = None
            if order.rider:
                rider_data = {
                    "full_name": order.rider.get_full_name() or "Ibrahim Sanni",
                    "phone_number": getattr(order.rider, 'phone_number', '+234 803 123 4567'),
                    "rating": "4.9",
                    "total_trips": 342,
                    "vehicle_model": "Yamaha Safar 125cc",
                    "plate_number": "LSR-849-QE",
                    "eta": "2 mins away",
                }

            return Response({
                "status": order.status,
                "order": OrderSerializer(order).data,
                "rider": rider_data
            })
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        """Rider endpoint to update progress, track demurrage, and deduct commission"""
        try:
            order = Order.objects.get(pk=pk, rider=request.user)
            new_status = request.data.get('status')
            entered_pin = request.data.get('dropoff_pin')

            if new_status == 'IN_TRANSIT':
                order.status = 'IN_TRANSIT'
                order.in_transit_at = timezone.now()
                order.save()
                return Response({"message": "Order is now in transit.", "order": OrderSerializer(order).data})

            elif new_status == 'ARRIVED_DROPOFF':
                order.status = 'ARRIVED_DROPOFF'
                order.arrived_at_dropoff_at = timezone.now()
                order.save()
                return Response({"message": "Arrival logged at drop-off. 5-minute grace period active.", "order": OrderSerializer(order).data})

            elif new_status == 'COMPLETED':
                if entered_pin and entered_pin == order.dropoff_pin:
                    order.completed_at = timezone.now()
                    order.final_earnings = Decimal(str(order.dynamic_earnings))
                    order.status = 'COMPLETED'
                    order.save()

                    # Deduct 10% platform commission from rider's wallet
                    commission = (order.final_earnings * Decimal('0.10')).quantize(Decimal('0.01'))
                    wallet = RiderWallet.objects.get(rider=request.user)
                    wallet.balance -= commission
                    wallet.save()

                    return Response({
                        "message": "Delivery completed successfully!",
                        "final_payout": f"₦{order.final_earnings:,.0f}",
                        "commission_deducted": f"₦{commission}",
                        "new_wallet_balance": f"₦{wallet.balance}",
                        "order": OrderSerializer(order).data
                    })
                else:
                    return Response({"error": "Invalid 4-digit drop-off PIN."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"error": "Invalid status transition."}, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

class OrderMessageListCreateView(generics.ListCreateAPIView):
    """Fetch messages or send a new message for a specific order"""
    serializer_class = OrderMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return OrderMessage.objects.filter(order_id=self.kwargs['order_id'])

    def perform_create(self, serializer):
        order = Order.objects.get(pk=self.kwargs['order_id'])
        serializer.save(sender=self.request.user, order=order)