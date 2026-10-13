from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.db.models import Q
from django.utils import timezone
from .models import OTPLog, RiderProfile, CustomerProfile

User = get_user_model()


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6)


class UserRegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="An account with this email address already exists."
            )
        ]
    )
    phone_number = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="An account with this phone number already exists."
            )
        ]
    )


    password = serializers.CharField(write_only=True, min_length=6, required=True)
    profile_picture = serializers.ImageField(required=False, write_only=True)

    class Meta:
        model = User
        fields = [
            'phone_number', 
            'first_name', 
            'last_name', 
            'email', 
            'role', 
            'password', 
            'profile_picture'
        ]

    def create(self, validated_data):
        profile_picture = validated_data.pop('profile_picture', None)
        role = validated_data.get('role', getattr(User.Role, 'CUSTOMER', 'CUSTOMER'))
        phone = validated_data.get('phone_number', '')
        email = validated_data.get('email', '')
        password = validated_data.get('password')

        user = User.objects.create_user(
            username=phone if phone else email,
            email=email,
            password=password,
            phone_number=phone,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=role,
            is_phone_verified=True
        )

        if role == getattr(User.Role, 'RIDER', 'RIDER'):
            RiderProfile.objects.create(user=user)
        else:
            CustomerProfile.objects.create(
                user=user, 
                profile_picture=profile_picture
            )

        return user


# authentication/serializers.py
# authentication/serializers.py


class RiderProfileSerializer(serializers.ModelSerializer):
    vehicle_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = RiderProfile
        fields = [
            'id', 
            'nin_number', 'nin_id_card_image', 'live_selfie', 
            'residential_address',
            'vehicle_type', 'plate_number', 'vehicle_make', 
            'vehicle_model', 'vehicle_year', 'vehicle_color', 
            'vehicle_photo', 'driver_license', 'vehicle_insurance', 'road_worthiness',
            'nipost_permit', 'lasaa_permit', 'riders_card',
            'emergency_full_name', 'emergency_phone_number', 'emergency_relationship',
            'bank_name', 'account_number', 'account_name',
            'is_available', 'verification_status', 'admin_note', 'currency'
        ]
        read_only_fields = ['verification_status', 'admin_note']

        extra_kwargs = {
            field: {'required': False, 'allow_null': True}
            for field in fields if field not in ['id', 'verification_status', 'admin_note', 'vehicle_type']
        }

    def validate_vehicle_type(self, value):
        if not value:
            return value
            
        # Clean and map to match your exact uppercase model choices
        cleaned = str(value).strip().lower()
        mapping = {
            'bicycle': 'BICYCLE',
            'motorcycle': 'MOTORCYCLE',
            'car': 'CAR'
        }
        
        return mapping.get(cleaned, value.upper())
    
class CustomerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            'id', 
            'email', 
            'phone_number', 
            'first_name',
            'last_name',
            'default_address', 
            'longitude',
            'latitude',
            'profile_picture'
        ]


class LoginSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        identifier = attrs.get('email_or_phone', '').strip().lower()
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError("Both email/phone and password are required.")

        user = None
        if '@' in identifier:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(phone_number=identifier)
            except User.DoesNotExist:
                pass

        if user is None or not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials. Check your email/phone or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is inactive.")

        refresh = RefreshToken.for_user(user)

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': getattr(user, 'phone_number', ''),
                'role': getattr(user, 'role', 'CUSTOMER'),
            }
        }




class VerifyOTPOnlySerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True, write_only=True)
    otp_code = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        raw_identifier = attrs.get('identifier', '').strip()
        otp_code = attrs.get('otp_code', '').strip()

        user = User.objects.filter(
            Q(email__iexact=raw_identifier) | Q(phone_number=raw_identifier)
        ).first()

        if not user:
            raise serializers.ValidationError({
                "identifier": ["No account found with this email or phone number."]
            })

        otp_record = OTPLog.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False
        ).order_by('-created_at').first()

        if not otp_record:
            raise serializers.ValidationError({
                "otp_code": ["Invalid verification code."]
            })

        if timezone.now() > otp_record.created_at + timedelta(minutes=10):
            otp_record.is_used = True
            otp_record.save(update_fields=['is_used'])
            raise serializers.ValidationError({
                "otp_code": ["Verification code has expired. Please request a new one."]
            })

        attrs['user'] = user
        attrs['otp_record'] = otp_record
        return attrs



class RequestPasswordResetOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        required=True,
        error_messages={"blank": "Email or phone number is required."}
    )

class ResetPasswordWithOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=True)
    otp_code = serializers.CharField(max_length=6, min_length=6, required=True)
    new_password = serializers.CharField(min_length=6, write_only=True, required=True)

    def validate(self, attrs):
        raw_identifier = attrs.get('identifier', '').strip()
        otp_code = attrs.get('otp_code', '').strip()

        # 1. Lookup User
        user = User.objects.filter(
            Q(email__iexact=raw_identifier) | Q(phone_number=raw_identifier)
        ).first()

        if not user:
            raise serializers.ValidationError({"identifier": "No account found with this email or phone number."})

        # 2. Lookup unused OTP log
        otp_record = OTPLog.objects.filter(
            user=user,
            otp_code=otp_code,
            is_used=False
        ).order_by('-created_at').first()

        if not otp_record:
            raise serializers.ValidationError({"otp_code": "Invalid verification code."})

        # 3. Check Expiry (10 minutes)
        if timezone.now() > otp_record.created_at + timedelta(minutes=10):
            raise serializers.ValidationError({"otp_code": "Verification code has expired. Please request a new one."})

        attrs['user'] = user
        attrs['otp_record'] = otp_record
        return attrs

    def save(self):
        user = self.validated_data['user']
        otp_record = self.validated_data['otp_record']
        new_password = self.validated_data['new_password']

        # Update password
        user.set_password(new_password)
        user.save()

        # Mark OTP as used
        otp_record.is_used = True
        otp_record.save()

        return user
