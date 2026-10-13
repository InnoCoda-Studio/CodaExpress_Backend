from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_request



class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        RIDER = "RIDER", "Rider"
        ADMIN = "ADMIN", "Admin"

    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, max_length=255)
    role = models.CharField(max_length=10, default=Role.CUSTOMER, choices=Role.choices)
    is_phone_verified = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    blocked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} - ({self.role})"

    
class OTPLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="otp_logs",
        null=True, 
        blank=True
    )
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        target = self.email or self.phone_number or f"User {self.user_id}"
        return f"OTP for {target} - Used: {self.is_used}"
    

class RiderProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        INCOMPLETE = "INCOMPLETE", "Incomplete"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        NEEDS_CORRECTION = "NEEDS_CORRECTION", "Needs Correction"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    class VehicleType(models.TextChoices):
        BICYCLE = "BICYCLE", "Bicycle"
        MOTORCYCLE = "MOTORCYCLE", "motorcycle"
        CAR    = "CAR", "Car"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rider_profile"
    )

    # 1. Identity Verification (Screens 2 & 4)
    nin_number = models.CharField(max_length=11, unique=True, null=True, blank=True)
    nin_id_card_image = models.ImageField(upload_to="riders/ids/", null=True, blank=True)
    live_selfie = models.ImageField(upload_to="riders/selfies/", null=True, blank=True)
    rider_profile = models.ImageField(upload_to="riders/profiles/", null=True, blank=True)

    # 2. Basic Contact & Residential Info (Screen 2)
    residential_address = models.CharField(max_length=200, blank=True, null=True)

    # 3. Vehicle & Insurance Details (Screens 3, 5 & 6)
    vehicle_type = models.CharField(
        max_length=15, choices=VehicleType.choices, default=VehicleType.BICYCLE
    )
    plate_number = models.CharField(max_length=15, blank=True, null=True)
    vehicle_make = models.CharField(max_length=50, blank=True, null=True)
    vehicle_model = models.CharField(max_length=50, blank=True, null=True)
    vehicle_year = models.CharField(max_length=4, blank=True, null=True)
    vehicle_color = models.CharField(max_length=30, blank=True, null=True)
    vehicle_photo = models.ImageField(upload_to="riders/vehicles/", blank=True, null=True)
    driver_license = models.ImageField(upload_to="riders/licenses/", blank=True, null=True)
    vehicle_insurance = models.ImageField(upload_to="riders/insurance/", blank=True, null=True)

    # 4. Emergency Contact (Screen 7)
    emergency_full_name = models.CharField(max_length=200, blank=True, null=True)
    emergency_phone_number = models.CharField(max_length=20, blank=True, null=True)
    emergency_relationship = models.CharField(max_length=50, blank=True, null=True)

    # 5. Payout / Bank Information (Screen 8)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=10, blank=True, null=True)
    account_name = models.CharField(max_length=200, blank=True, null=True)

    # 6. Operational & Admin Control (Screens 10, 11 & 15)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.INCOMPLETE,
    )
    is_available = models.BooleanField(default=False)
    
    admin_note = models.TextField(max_length=800, blank=True, null=True)
    currency = models.CharField(max_length=3, default="NGN")
    road_worthiness = models.ImageField(
        upload_to="riders/road_worthiness/", blank=True, null=True
    )
    # Lagos & Federal Regulatory Permits
    nipost_permit = models.ImageField(upload_to="riders/nipost/", blank=True, null=True)
    lasaa_permit = models.ImageField(upload_to="riders/lasaa/", blank=True, null=True)
    riders_card = models.ImageField(upload_to="riders/riders_card/", blank=True, null=True)


    def __str__(self):
        return f"{self.user.username} - {self.vehicle_type} ({self.verification_status})"

    
class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )
    profile_picture = models.ImageField(upload_to="customers/profiles/", null=True, blank=True)
    default_address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"Customer Profile: {self.user.email}"


