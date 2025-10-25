"""
Views for user authentication using MongoEngine and MongoDB.
Includes proper error handling and user-friendly error messages.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from mongoengine.errors import ValidationError, NotUniqueError, DoesNotExist
import logging

from .models import User, EmailVerificationOTP, PasswordResetToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    OTPVerificationSerializer,
    SendOTPSerializer,
    get_tokens_for_user
)

logger = logging.getLogger(__name__)


class RegisterView(APIView):
    """
    User registration endpoint with email verification.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create user
            try:
                user = serializer.save()
            except NotUniqueError as e:
                return Response({
                    'error': 'Registration failed',
                    'message': 'A user with this email or username already exists.'
                }, status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as e:
                return Response({
                    'error': 'Validation error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate OTP
            try:
                otp = EmailVerificationOTP.create_for_user(user)
                
                # Send OTP email
                try:
                    send_mail(
                        subject='Verify Your Email - Artvinci',
                        message=f'Your verification code is: {otp.code}\n\nThis code will expire in 10 minutes.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    logger.info(f"OTP sent to {user.email}: {otp.code}")
                except Exception as e:
                    logger.error(f"Email sending error: {str(e)}")
                    # Don't fail registration if email fails
                
                return Response({
                    'message': 'Account created successfully. Please check your email for verification code.',
                    'user': UserSerializer(user).data,
                    'email': user.email,
                    'requires_verification': True
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"OTP creation error: {str(e)}")
                # Delete user if OTP creation fails
                user.delete()
                return Response({
                    'error': 'Registration failed',
                    'message': 'Failed to send verification code. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'error': 'Registration failed',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    """
    User login endpoint.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Login failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = serializer.validated_data['user']
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            # Generate tokens
            tokens = get_tokens_for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                **tokens
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'error': 'Login failed',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyOTPView(APIView):
    """
    Verify OTP code and activate user account.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = OTPVerificationSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Verification failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user = serializer.validated_data['user']
            otp = serializer.validated_data['otp']
            
            # Mark OTP as used
            otp.is_used = True
            otp.save()
            
            # Activate user account
            user.is_verified = True
            user.save()
            
            # Generate tokens
            tokens = get_tokens_for_user(user)
            
            logger.info(f"User verified successfully: {user.email}")
            
            return Response({
                'message': 'Email verified successfully',
                'user': UserSerializer(user).data,
                **tokens
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            return Response({
                'error': 'Verification failed',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendOTPView(APIView):
    """
    Resend OTP code to user's email.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            serializer = SendOTPSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Failed to send code',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            email = serializer.validated_data['email']
            user = User.objects(email=email).first()
            
            # Generate new OTP
            try:
                otp = EmailVerificationOTP.create_for_user(user)
                
                # Send OTP email
                try:
                    send_mail(
                        subject='Verify Your Email - Artvinci',
                        message=f'Your verification code is: {otp.code}\n\nThis code will expire in 10 minutes.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    logger.info(f"OTP resent to {user.email}: {otp.code}")
                except Exception as e:
                    logger.error(f"Email sending error: {str(e)}")
                    return Response({
                        'error': 'Email sending failed',
                        'message': 'Failed to send verification code. Please try again later.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({
                    'message': 'Verification code sent successfully'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"OTP creation error: {str(e)}")
                return Response({
                    'error': 'Failed to send code',
                    'message': 'An unexpected error occurred. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.error(f"Send OTP error: {str(e)}")
            return Response({
                'error': 'Failed to send code',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserProfileView(APIView):
    """
    Get or update user profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user profile."""
        try:
            # request.user is now a MongoEngine User document (from our custom auth)
            user = request.user
            
            if not user:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response(
                UserSerializer(user).data,
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}")
            return Response({
                'error': 'Failed to fetch profile',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request):
        """Update user profile including profile image."""
        try:
            # request.user is now a MongoEngine User document (from our custom auth)
            user = request.user
            
            if not user:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get update data
            data = request.data.copy()
            
            # Update basic fields
            if 'username' in data and data['username'] != user.username:
                # Check if username is unique
                existing_user = User.objects(username=data['username']).first()
                if existing_user and str(existing_user.id) != str(user.id):
                    return Response({
                        'error': 'Username already taken',
                        'errors': {'username': ['This username is already in use']}
                    }, status=status.HTTP_400_BAD_REQUEST)
                user.username = data['username']
            
            if 'first_name' in data:
                user.first_name = data['first_name']
            
            if 'last_name' in data:
                user.last_name = data['last_name']
            
            if 'bio' in data:
                user.bio = data['bio']
            
            # Handle profile image upload
            if 'profile_image' in request.FILES:
                profile_image = request.FILES['profile_image']
                
                try:
                    import cloudinary.uploader
                    
                    # Upload to Cloudinary
                    logger.info(f"Uploading profile image: {profile_image.name}")
                    upload_result = cloudinary.uploader.upload(
                        profile_image,
                        folder='artvinci/profiles',
                        public_id=f'user_{user.id}',
                        overwrite=True,
                        resource_type='image',
                        transformation=[
                            {'width': 500, 'height': 500, 'crop': 'fill', 'gravity': 'face'},
                            {'quality': 'auto', 'fetch_format': 'auto'}
                        ]
                    )
                    
                    # Store Cloudinary URL
                    user.profile_image = upload_result['secure_url']
                    logger.info(f"Profile image uploaded successfully: {user.profile_image}")
                    
                except Exception as upload_error:
                    logger.error(f"Image upload error: {str(upload_error)}")
                    # Continue with other updates even if image upload fails
                    return Response({
                        'error': 'Image upload failed',
                        'message': str(upload_error)
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save user
            try:
                user.save()
                logger.info(f"Profile updated successfully for user: {user.username}")
            except NotUniqueError:
                return Response({
                    'error': 'Username already exists',
                    'errors': {'username': ['This username is already in use']}
                }, status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as e:
                return Response({
                    'error': 'Validation error',
                    'errors': e.to_dict()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'message': 'Profile updated successfully',
                'user': user.to_dict()
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'error': 'Failed to update profile',
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ForgotPasswordView(APIView):
    """
    Request password reset - sends email with reset token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            email = request.data.get('email')
            
            if not email:
                return Response({
                    'error': 'Email is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find user by email
            try:
                user = User.objects(email=email).first()
                
                if not user:
                    # Don't reveal if email exists or not (security)
                    return Response({
                        'message': 'If an account exists with this email, you will receive a password reset link.'
                    }, status=status.HTTP_200_OK)
                
                # Generate reset token
                reset_token = PasswordResetToken.create_for_user(user)
                
                # Send reset email
                reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token.token}"
                
                try:
                    send_mail(
                        subject='Reset Your Password - Artvinci',
                        message=f'''
Hello {user.first_name or user.username},

You requested to reset your password. Click the link below to reset it:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.

Best regards,
The Artvinci Team
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    logger.info(f"Password reset email sent to {user.email}")
                    logger.info(f"Reset token: {reset_token.token}")  # For development
                except Exception as e:
                    logger.error(f"Email sending error: {str(e)}")
                    return Response({
                        'error': 'Failed to send reset email. Please try again later.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                return Response({
                    'message': 'If an account exists with this email, you will receive a password reset link.'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Forgot password error: {str(e)}")
                return Response({
                    'message': 'If an account exists with this email, you will receive a password reset link.'
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}")
            return Response({
                'error': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResetPasswordView(APIView):
    """
    Reset password with token.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            token = request.data.get('token')
            new_password = request.data.get('password')
            
            if not token or not new_password:
                return Response({
                    'error': 'Token and new password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate password length
            if len(new_password) < 8:
                return Response({
                    'error': 'Password must be at least 8 characters long'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find reset token
            try:
                reset_token = PasswordResetToken.objects(token=token).first()
                
                if not reset_token:
                    return Response({
                        'error': 'Invalid or expired reset token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if token is valid
                if not reset_token.is_valid():
                    return Response({
                        'error': 'Invalid or expired reset token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Get user and update password
                user = reset_token.user
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                
                logger.info(f"Password reset successful for user: {user.email}")
                
                return Response({
                    'message': 'Password reset successful. You can now login with your new password.'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Reset password error: {str(e)}")
                return Response({
                    'error': 'Invalid or expired reset token'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"Reset password error: {str(e)}")
            return Response({
                'error': 'An unexpected error occurred. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
