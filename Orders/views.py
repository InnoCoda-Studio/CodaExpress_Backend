from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, OrderMessage
from .serializers import OrderSerializer, OrderMessageSerializer
import random

class CreateOrderView(generics.CreateAPIView):
    """Customer endpoint to book a new delivery run"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Generate a random 4-digit PIN for secure drop-off verification
        pin = f"{random.randint(1000, 9999)}"
        serializer.save(customer=self.request.user, status='PENDING', dropoff_pin=pin)


class CustomerOrderListView(generics.ListAPIView):
    """Customer endpoint to view all their booked deliveries"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')


class AvailableOrdersListView(generics.ListAPIView):
    """Rider endpoint to see pending orders searching for a dispatch"""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(status='PENDING').order_by('-created_at')


class AcceptOrderView(APIView):
    """Rider endpoint to claim an incoming order"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            if order.status != 'PENDING':
                return Response({"error": "Order has already been taken or cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            
            order.rider = request.user
            order.status = 'ACCEPTED'
            order.save()

            serializer = OrderSerializer(order)
            return Response({"message": "Order accepted successfully!", "order": serializer.data}, status=status.HTTP_200_OK)
        
        except Order.DoesNotExist:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)


class UpdateOrderStatusView(APIView):
    """Rider endpoint to update progress (e.g. IN_TRANSIT, or verify PIN to complete)"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, rider=request.user)
            new_status = request.data.get('status')
            entered_pin = request.data.get('dropoff_pin')

            if new_status == 'IN_TRANSIT':
                order.status = 'IN_TRANSIT'
                order.save()
                return Response({"message": "Order is now in transit.", "order": OrderSerializer(order).data})

            elif new_status == 'COMPLETED':
                # Verify 4-digit PIN before completing delivery
                if entered_pin and entered_pin == order.dropoff_pin:
                    order.status = 'COMPLETED'
                    order.save()
                    return Response({"message": "Delivery completed successfully! Wallet credited.", "order": OrderSerializer(order).data})
                else:
                    return Response({"error": "Invalid 4-digit drop-off PIN."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"error": "Invalid status transition."}, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)


class OrderMessageListCreateView(generics.ListCreateAPIView):
    """Fetch messages or send a new message for a specific order (Customer & Rider chat)"""
    serializer_class = OrderMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        order_id = self.kwargs['order_id']
        return OrderMessage.objects.filter(order_id=order_id)

    def perform_create(self, serializer):
        order_id = self.kwargs['order_id']
        order = Order.objects.get(pk=order_id)
        serializer.save(sender=self.request.user, order=order)