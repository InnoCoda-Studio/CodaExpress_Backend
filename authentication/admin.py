# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPLog, RiderProfile, CustomerProfile
from django.utils.html import format_html

@admin.register(RiderProfile)
class RiderProfileAdmin(admin.ModelAdmin):
    """
    Organized Rider Profile Admin: Displays rider full name, vehicle tiers,
    documents with image previews, bulk approval actions, and verification details.
    """
    actions = ['approve_selected_riders', 'reject_selected_riders']

    list_display = (
        'rider_full_name',
        'user',
        'colored_vehicle_type',
        'colored_status',
        'nin_number',
        'bank_name',
        'account_number',
        'is_available'
    )

    list_filter = (
        'verification_status',
        'vehicle_type',
        'is_available',
        'bank_name'
    )

    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__email',
        'user__phone_number',
        'nin_number',
        'plate_number',
        'account_number',
        'bank_name',
        'emergency_full_name'
    )

    readonly_fields = (
        'rider_full_name',
        'user',
        'nin_id_card_image_preview',
        'live_selfie_preview',
        'vehicle_photo_preview',
        'driver_license_preview',
        'vehicle_insurance_preview',
        'road_worthiness_preview',
        'riders_card_preview',
    )

    # Neatly organized fieldsets so admin scrolling is clean and structured
    fieldsets = (
        ('Account & Verification Overview', {
            'fields': ('rider_full_name', 'user', 'verification_status', 'is_available', 'admin_note', 'currency')
        }),
        ('1. Identity & Personal Info', {
            'fields': (
                'nin_number',
                'nin_id_card_image',
                'nin_id_card_image_preview',
                'live_selfie',
                'live_selfie_preview',
                'residential_address'
            )
        }),
        ('2. Vehicle & Documentation Details', {
            'fields': (
                'vehicle_type',
                'plate_number',
                'vehicle_make',
                'vehicle_model',
                'vehicle_year',
                'vehicle_color',
                'vehicle_photo',
                'vehicle_photo_preview',
                'driver_license',
                'driver_license_preview',
                'vehicle_insurance',
                'vehicle_insurance_preview',
                'road_worthiness',
                'road_worthiness_preview',
                'nipost_permit',
                'lasaa_permit',
                'riders_card',
                'riders_card_preview',
            )
        }),
        ('3. Emergency Contact', {
            'fields': ('emergency_full_name', 'emergency_phone_number', 'emergency_relationship')
        }),
        ('4. Payout / Bank Account Info', {
            'fields': ('bank_name', 'account_number', 'account_name')
        }),
    )

    @admin.action(description="Approve selected riders")
    def approve_selected_riders(self, request, queryset):
        updated_count = queryset.update(
            verification_status=RiderProfile.VerificationStatus.APPROVED,
            is_available=True,
        )
        self.message_user(
            request,
            f"{updated_count} rider(s) approved and marked available for dispatch."
        )

    @admin.action(description="Reject selected riders")
    def reject_selected_riders(self, request, queryset):
        updated_count = queryset.update(
            verification_status=RiderProfile.VerificationStatus.REJECTED,
            is_available=False,
        )
        self.message_user(
            request,
            f"{updated_count} rider(s) marked as rejected.",
            level="WARNING",
        )

    # Display Rider's Full Name (falls back to username if blank)
    def rider_full_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name if full_name else obj.user.username
    rider_full_name.short_description = "Rider Name"
    rider_full_name.admin_order_field = 'user__first_name'

    # Visual badge for Vehicle Type in Admin List
    def colored_vehicle_type(self, obj):
        colors = {
            'BICYCLE': '#0ea5e9',   # Sky Blue
            'MOTORCYCLE': '#f59e0b',# Amber
            'CAR': '#10b981'        # Emerald
        }
        color = colors.get(obj.vehicle_type, '#64748B')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_vehicle_type_display()
        )
    colored_vehicle_type.short_description = "Vehicle Tier"

    # Visual badge for Verification Status in Admin List
    def colored_status(self, obj):
        colors = {
            'INCOMPLETE': '#64748B',      # Slate
            'UNDER_REVIEW': '#3b82f6',    # Blue
            'NEEDS_CORRECTION': '#f97316',# Orange
            'APPROVED': '#22c55e',        # Green
            'REJECTED': '#ef4444'         # Red
        }
        color = colors.get(obj.verification_status, '#64748B')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    colored_status.short_description = "Status"

    # Reusable helper for safe image thumbnails in Django Admin
    def _render_preview(self, image_field, empty_text):
        if image_field:
            return format_html(
                '<img src="{}" style="max-height: 180px; max-width: 280px; object-fit: contain; border-radius: 8px; border: 1px solid #DCEAF2;" />',
                image_field.url
            )
        return empty_text

    def nin_id_card_image_preview(self, obj):
        return self._render_preview(obj.nin_id_card_image, "No NIN Card Uploaded")
    nin_id_card_image_preview.short_description = "NIN Card Preview"

    def live_selfie_preview(self, obj):
        return self._render_preview(obj.live_selfie, "No Selfie Uploaded")
    live_selfie_preview.short_description = "Selfie Preview"

    def vehicle_photo_preview(self, obj):
        return self._render_preview(obj.vehicle_photo, "No Vehicle Photo Uploaded")
    vehicle_photo_preview.short_description = "Vehicle Photo Preview"

    def driver_license_preview(self, obj):
        return self._render_preview(obj.driver_license, "No Driver's License Uploaded")
    driver_license_preview.short_description = "Driver's License Preview"

    def vehicle_insurance_preview(self, obj):
        return self._render_preview(obj.vehicle_insurance, "No Vehicle Insurance Uploaded")
    vehicle_insurance_preview.short_description = "Vehicle Insurance Preview"

    def road_worthiness_preview(self, obj):
        return self._render_preview(obj.road_worthiness, "No Road Worthiness Uploaded")
    road_worthiness_preview.short_description = "Road Worthiness Preview"

    def riders_card_preview(self, obj):
        return self._render_preview(obj.riders_card, "No Rider's Card Uploaded")
    riders_card_preview.short_description = "Rider's Card Preview"