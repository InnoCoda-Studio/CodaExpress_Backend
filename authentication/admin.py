# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPLog, RiderProfile, CustomerProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Extends Django's default UserAdmin to support your custom roles,
    phone numbers, verification status, and block controls.
    """
    list_display = ('username', 'email', 'phone_number', 'role', 'is_phone_verified', 'is_blocked', 'is_staff')
    list_filter = ('role', 'is_phone_verified', 'is_blocked', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'phone_number')
    
    # Extend fieldsets so custom fields appear nicely when editing a user in Admin
    fieldsets = UserAdmin.fieldsets + (
        ('CodaExpress Custom Settings', {
            'fields': ('phone_number', 'role', 'is_phone_verified', 'is_blocked', 'blocked_until')
        }),
    )

@admin.register(OTPLog)
class OTPLogAdmin(admin.ModelAdmin):
    """
    Allows tracking of generated OTP codes for debugging and security audits.
    """
    list_display = ('target_display', 'otp_code', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('phone_number', 'email', 'user__username')
    readonly_fields = ('created_at',)

    def target_display(self, obj):
        return obj.email or obj.phone_number or (obj.user.username if obj.user else "N/A")
    target_display.short_description = "OTP Target"

@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    """
    Crucial for reviewing and updating rider verification statuses,
    viewing submitted documents, and checking payout details.
    """
    list_display = (
        'user', 'vehicle_type', 'verification_status', 
        'is_available', 'nin_number', 'bank_name', 'account_number'
    )
    list_filter = ('verification_status', 'vehicle_type', 'is_available')
    search_fields = (
        'user__username', 'user__email', 'nin_number', 
        'plate_number', 'account_number', 'bank_name'
    )
    readonly_fields = ('user',)

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Manages customer details and saved locations.
    """
    list_display = ('user', 'default_address', 'latitude', 'longitude')
    search_fields = ('user__username', 'user__email', 'default_address')
    readonly_fields = ('user',)