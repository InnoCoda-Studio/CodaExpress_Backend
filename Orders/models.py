from django.db import models
from django.conf import settings

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='customer_orders'
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='rider_deliveries'
    )
    
    # Pickup Details (Sender / Store / Vendor)
    pickup_address = models.CharField(max_length=255)
    pickup_contact_name = models.CharField(max_length=150, blank=True, null=True)
    pickup_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    descriptions  = models.CharField(max_length=350, null=True, blank=True)
    
    # Drop-off Details (Recipient / Customer)
    dropoff_address = models.CharField(max_length=255)
    dropoff_contact_name = models.CharField(max_length=150, blank=True, null=True)
    dropoff_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Package & Financials
    package_type = models.CharField(max_length=100)
    distance = models.CharField(max_length=50, default="3.5 km")
    estimated_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=2600.00)
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    dropoff_pin = models.CharField(max_length=4, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - Pickup: {self.pickup_contact_name} | Dropoff: {self.dropoff_contact_name}"


class OrderMessage(models.Model):
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    message_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg on Order #{self.order.id} by {self.sender.username}"