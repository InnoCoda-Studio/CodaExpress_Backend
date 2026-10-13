from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SendOTPView,
    VerifyOTPView, 
    RegisterView,
    LoginView,
    RequestPasswordResetOTPView, 
    ResetPasswordWithOTPView,
    VerifyPasswordResetOTPView,
    RiderProfileOnboardingView,
    verify_nin,
    VerifyBankAccountView,
    # GoogleLoginView,
    # FacebookLoginView,
)

urlpatterns = [
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('request-password-reset-otp/', RequestPasswordResetOTPView.as_view(), name='request_password_reset_otp'),
    path('reset-password-otp/', ResetPasswordWithOTPView.as_view(), name='reset_password_otp'),
    path('verify-reset-otp/', VerifyPasswordResetOTPView.as_view(), name='verify-otp'),

    # path('google/', GoogleLoginView.as_view(), name='google_login'),
    # path('facebook/', FacebookLoginView.as_view(), name='facebook_login'),

    # Real-time NIN Verification
    path('verify-nin/', verify_nin, name='verify-nin'),

    path('verify-bank-account/', VerifyBankAccountView.as_view(), name='verify-bank-account'),
    path('riders/onboarding/', RiderProfileOnboardingView.as_view(), name='rider-onboarding'),
]





