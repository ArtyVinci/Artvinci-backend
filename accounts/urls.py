from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    SendOTPView,
    VerifyOTPView,
    UserProfileView,
    ForgotPasswordView,
    ResetPasswordView
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    # OTP verification endpoints
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    # Password reset endpoints
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    
    # Token refresh
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile endpoints
    path('me/', UserProfileView.as_view(), name='profile'),
]
