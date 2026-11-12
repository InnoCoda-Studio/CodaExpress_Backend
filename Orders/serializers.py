from rest_framework import serializers
from .models import Order, OrderMessage

class OrderSerializer(serializers.ModelSerializer):
    dynamic_earnings = serializers.FloatField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 
            'pickup_address', 'pickup_contact_name', 'pickup_contact_phone', 'descriptions',
            'dropoff_address', 'dropoff_contact_name', 'dropoff_contact_phone',
            'package_type', 'required_vehicle', 'distance', 'base_earnings', 'dynamic_earnings', 
            'rider', 'status', 'dropoff_pin', 'created_at'
        ]
        read_only_fields = ['customer', 'rider', 'status', 'dropoff_pin', 'created_at', 'base_earnings', 'dynamic_earnings']


class OrderMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)

    class Meta:
        model = OrderMessage
        fields = ['id', 'order', 'sender', 'sender_name', 'sender_role', 'message_text', 'created_at']
        read_only_fields = ['sender', 'order', 'created_at']