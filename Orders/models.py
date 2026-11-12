from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone

class RiderWallet(models.Model):
    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet: {self.rider.username} - ₦{self.balance}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        ARRIVED_DROPOFF = "ARRIVED_DROPOFF", "Arrived at Drop-off"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class VehicleRequirement(models.TextChoices):
        BICYCLE = "BICYCLE", "Bicycle"
        MOTORCYCLE = "MOTORCYCLE", "Motorcycle"
        CAR = "CAR", "Car"

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
    
    # 1. Pickup Details (Sender / Store / Vendor)
    pickup_address = models.CharField(max_length=255)
    pickup_contact_name = models.CharField(max_length=150, blank=True, null=True)
    pickup_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    descriptions = models.CharField(max_length=350, null=True, blank=True)
    
    # 2. Drop-off Details (Recipient / Customer)
    dropoff_address = models.CharField(max_length=255)
    dropoff_contact_name = models.CharField(max_length=150, blank=True, null=True)
    dropoff_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    
    # 3. Package & Vehicle Tier Routing
    package_type = models.CharField(max_length=100)
    required_vehicle = models.CharField(
        max_length=15, 
        choices=VehicleRequirement.choices, 
        default=VehicleRequirement.MOTORCYCLE
    )
    distance = models.CharField(max_length=50, default="3.5 km")
    base_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=2600.00)
    final_earnings = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    dropoff_pin = models.CharField(max_length=4, blank=True, null=True)
    
    # 4. Timestamps for Surge & Demurrage Calculation
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    in_transit_at = models.DateTimeField(null=True, blank=True)
    arrived_at_dropoff_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def dynamic_earnings(self):
        """Calculates progressive surge, vehicle multiplier, and waiting/traffic delays"""
        if self.status == self.Status.COMPLETED and self.final_earnings is not None:
            return float(self.final_earnings)

        now = timezone.now()
        
        # Vehicle pricing multipliers matching your RiderProfile choices
        multipliers = {
            'BICYCLE': 0.85,
            'MOTORCYCLE': 1.0,
            'CAR': 1.8,
        }
        multiplier = multipliers.get(self.required_vehicle, 1.0)
        amount = float(self.base_earnings) * multiplier

        # PHASE 1: Progressive Surge while PENDING (10% compounding every 2 mins)
        if self.status == self.Status.PENDING:
            elapsed_mins = (now - self.created_at).total_seconds() / 60
            for _ in range(int(elapsed_mins // 2)):
                amount *= 1.10
            return round(amount, -1)

        # PHASE 2: In-Transit Traffic Delay Fee
        if self.in_transit_at:
            transit_end = self.arrived_at_dropoff_at or self.completed_at or now
            transit_mins = (transit_end - self.in_transit_at).total_seconds() / 60
            estimated_time = 15  # Normal baseline minutes
            if transit_mins > estimated_time:
                amount += (transit_mins - estimated_time) * 50.0  # ₦50/min traffic delay

        # PHASE 3: Drop-off Waiting Fee (5 min free grace period, then ₦50/min)
        if self.arrived_at_dropoff_at:
            wait_end = self.completed_at or now
            wait_mins = (wait_end - self.arrived_at_dropoff_at).total_seconds() / 60
            billable_wait = max(0, wait_mins - 5)
            amount += billable_wait * 50.0

        return round(amount, -1)

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