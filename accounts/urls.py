from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,

    LogoutView,

    SendOTPView,
    VerifyOTPView,
    UserProfileView,
    ForgotPasswordView,

    ResetPasswordView,
    GoogleLoginInitiateView,
    GoogleCallbackView,
    RegisterFaceView,
    RegisterFaceFromProfileView,
    FaceLoginView,
    FaceDebugView

)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),

    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Google OAuth endpoints
    path('google/login/', GoogleLoginInitiateView.as_view(), name='google_login'),
    path('google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    
    # Face Recognition endpoints
    path('face/register/', RegisterFaceView.as_view(), name='face_register'),
    path('face/register-from-profile/', RegisterFaceFromProfileView.as_view(), name='face_register_from_profile'),
    path('face/login/', FaceLoginView.as_view(), name='face_login'),
    path('face/debug/', FaceDebugView.as_view(), name='face_debug'),

    
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
