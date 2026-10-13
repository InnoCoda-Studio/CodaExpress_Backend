import random
import requests as http_requests

# Django & Auth
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

# Django REST Framework
from rest_framework.views import APIView
from rest_framework.response import Response
import requests

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django.db.models import Q
from rest_framework import generics , permissions
# JWT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

# Local Models & Serializers

from .models import User, OTPLog, RiderProfile, CustomerProfile
from django.db.models import Q
from .utils import send_otp_email, send_otp_sms
from .serializers import (
    SendOTPSerializer,
    VerifyOTPSerializer,
    UserRegisterSerializer,
    LoginSerializer,
    RiderProfileSerializer,
    RequestPasswordResetOTPSerializer,
    ResetPasswordWithOTPSerializer,
    VerifyOTPOnlySerializer,
    # FacebookAuthSerializer,
    # GoogleAuthSerializer,
)


User = get_user_model()


class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            code = str(random.randint(100000, 999999))
            
            OTPLog.objects.create(phone_number=phone_number, otp_code=code)
            print(f"DEBUG OTP FOR {phone_number} code: {code}")
            
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = serializer.validated_data['otp_code']

            otp_record = OTPLog.objects.filter(
                phone_number=phone_number,
                otp_code=otp_code
            ).first()

            if otp_record:
                otp_record.delete()
                
                # Check if user already exists
                user = User.objects.filter(phone_number=phone_number).first()
                
                if user:
                    # Existing user: Issue JWT tokens immediately
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        "message": "OTP verified successfully",
                        "is_registered": True,
                        "role": user.role,
                        "tokens": {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                        }
                    }, status=status.HTTP_200_OK)
                
                # New user: Tell React Native to route to Role Differentiation screen
                return Response({
                    "message": "OTP verified successfully",
                    "is_registered": False,
                    "phone_number": phone_number
                }, status=status.HTTP_200_OK)
            print("VALIDATION ERRORS:", serializer.errors)
            return Response({"error": "Invalid or expired OTP code"}, status=status.HTTP_400_BAD_REQUEST)
        print("VALIDATION ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens so user is logged in automatically
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": f"{user.get_role_display()} account created successfully",
                "user": {
                    "id": user.id,
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "role": user.role,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_tokens_for_user(user):
    """Helper to generate JWT access and refresh tokens."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_identifier = (
            request.data.get('email') or 
            request.data.get('username') or 
            request.data.get('email_or_phone')
        )
        password = request.data.get('password')

        serializer = LoginSerializer(data={
            'email_or_phone': raw_identifier,
            'password': password
        })

        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        
        errors = serializer.errors
        detail = errors.get('non_field_errors', [None])[0] or "Invalid login credentials."
        return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

# class GoogleAuthView(APIView):
#     def post(self, request):
#         ...

# class FacebookAuthView(APIView):
#     def post(self, request):
#   import random

User = get_user_model()


from .utils import send_otp_email, send_otp_sms  # Import both helpers


class RequestPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get('identifier', '').strip()

        if not identifier:
            return Response(
                {"identifier": ["Email or phone number is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(phone_number=identifier)
        ).first()

        if not user:
            return Response(
                {"identifier": ["No account exists with this email or phone number."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        otp_code = f"{random.randint(100000, 999999)}"

        # Invalidate older unused OTPs for this user
        OTPLog.objects.filter(user=user, is_used=False).update(is_used=True)

        # Create new OTP Log
        OTPLog.objects.create(
            user=user,
            email=user.email,
            phone_number=user.phone_number,
            otp_code=otp_code
        )

        # Route dynamically: Email vs SMS
        if '@' in identifier and user.email:
            send_otp_email(to_email=user.email, otp_code=otp_code)
            message = "Verification code sent to your email."
        elif user.phone_number:
            send_otp_sms(phone_number=user.phone_number, otp_code=otp_code)
            message = "Verification code sent to your phone number."
        else:
            return Response(
                {"detail": "No valid contact channel found for this account."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"detail": message}, status=status.HTTP_200_OK)


class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPOnlySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"detail": "Verification code is valid."},
            status=status.HTTP_200_OK
        )
    
class ResetPasswordWithOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordWithOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(
            {"detail": "Password has been reset successfully. You can now log in."},
            status=status.HTTP_200_OK
        )

    
class RiderProfileOnboardingView(generics.RetrieveUpdateAPIView):
    serializer_class = RiderProfileSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        profile, created = RiderProfile.objects.get_or_create(user=self.request.user)
        return profile

    def update(self, request, *args, **kwargs):
        print("=== INCOMING PATCH DATA ===", request.data)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        # Automatically supply default values for required DB fields during multi-step patches
        serializer.save(is_available=False)

# authentication/views.py
class VerifyBankAccountView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        print("=== VERIFY BANK PAYLOAD ===", request.data) # Check terminal output!

        account_number = request.data.get("account_number")
        bank_code = request.data.get("bank_code")

        if not account_number or len(account_number) != 10:
            return Response(
                {"error": "Please enter a valid 10-digit account number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not bank_code:
            return Response(
                {"error": "bank_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        paystack_url = f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}"
        
        try:
            response = requests.get(paystack_url, headers=headers, timeout=10)
            res_data = response.json()

            print("=== PAYSTACK RESPONSE ===", res_data)

            if response.status_code == 200 and res_data.get("status"):
                data = res_data.get("data", {})
                return Response({
                    "verified": True,
                    "account_name": data.get("account_name"),
                    "account_number": data.get("account_number"),
                }, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"error": res_data.get("message", "Could not resolve bank account details.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except requests.exceptions.RequestException:
            return Response(
                {"error": "Bank verification service currently unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def verify_nin(request):
    nin_number = request.data.get('nin_number', '').strip()

    # 1. Validate Input
    if not nin_number or not nin_number.isdigit() or len(nin_number) != 11:
        return Response(
            {'verified': False, 'message': 'Please provide a valid 11-digit NIN.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 2. Retrieve & Clean Dojah Credentials
    dojah_secret = str(getattr(settings, 'DOJAH_SECRET_KEY', '')).strip()
    dojah_app_id = str(getattr(settings, 'DOJAH_APP_ID', '')).strip()

    if not dojah_secret or not dojah_app_id:
        return Response(
            {'verified': False, 'message': 'KYC service is currently unconfigured on the server.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 3. Determine Base URL (Sandbox vs Production)
    is_sandbox = dojah_secret.startswith('test_sk_') or dojah_secret.startswith('test_pk_')
    base_url = "https://sandbox.dojah.io" if is_sandbox else "https://api.dojah.io"
    endpoint_url = f"{base_url}/api/v1/kyc/nin?nin={nin_number}"

    headers = {
        "Authorization": dojah_secret,
        "AppId": dojah_app_id,
        "Accept": "application/json",
    }

    try:
        response = requests.get(endpoint_url, headers=headers, timeout=12)
        res_data = response.json()

        # 4. Handle Successful Verification
        if response.status_code == 200 and 'entity' in res_data:
            nin_entity = res_data['entity']
            return Response({
                'verified': True,
                'nin_data': {
                    'first_name': nin_entity.get('first_name'),
                    'last_name': nin_entity.get('last_name'),
                    'middle_name': nin_entity.get('middle_name'),
                    'gender': nin_entity.get('gender'),
                    'photo': nin_entity.get('photo'),
                }
            }, status=status.HTTP_200_OK)

        # 5. Handle Dojah Domain Errors (e.g. Wrong NIN / Unmatched Records)
        error_msg = res_data.get('error') or res_data.get('message') or 'NIN verification failed. Please verify the number.'
        return Response({'verified': False, 'message': error_msg}, status=status.HTTP_400_BAD_REQUEST)

    except requests.exceptions.Timeout:
        return Response(
            {'verified': False, 'message': 'Verification service timed out. Please try again.'},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    except requests.exceptions.RequestException:
        return Response(
            {'verified': False, 'message': 'Unable to reach identity provider. Check network connection.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )