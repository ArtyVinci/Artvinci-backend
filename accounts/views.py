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

import os
import base64
import io
import requests
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google_auth_oauthlib.flow import Flow
from urllib.parse import urlencode
from PIL import Image
import numpy as np
from deepface import DeepFace
import tempfile

# Face recognition temporarily disabled due to Python 3.14 compatibility issues
# TensorFlow doesn't support Python 3.14 yet - use Python 3.10-3.11 for face recognition


from .models import User, EmailVerificationOTP, PasswordResetToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    OTPVerificationSerializer,
    SendOTPSerializer,
    get_tokens_for_user
)
from .ai_service import user_ai_service

logger = logging.getLogger(__name__)



def extract_face_encoding_from_url(image_url, user_id=None):
    """
    Extract face encoding from an image URL (like Cloudinary).
    Returns face encoding as list of floats or None if no face detected.
    """
    try:
        # Download image from URL
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Open image
        image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_path = temp_file.name
            image.save(temp_path)
        
        try:
            # Extract face embedding using DeepFace with multi-detector strategy
            detectors = ['retinaface', 'mtcnn', 'opencv', 'ssd']
            embedding_objs = None
            
            for detector in detectors:
                try:
                    embedding_objs = DeepFace.represent(
                        img_path=temp_path,
                        model_name='Facenet',
                        enforce_detection=True,
                        detector_backend=detector,
                        align=True
                    )
                    if embedding_objs and len(embedding_objs) > 0:
                        logger.info(f"Face detected from URL using {detector}")
                        break
                except Exception as detector_error:
                    logger.warning(f"Detector {detector} failed for URL image: {str(detector_error)}")
                    continue
            
            if not embedding_objs or len(embedding_objs) == 0:
                logger.warning(f"No face detected in profile image URL: {image_url}")
                return None
            
            # Get the first face embedding and convert to list
            embedding = embedding_objs[0]['embedding']
            embedding_list = [float(x) for x in embedding]
            
            logger.info(f"Successfully extracted face encoding from URL for user {user_id or 'unknown'}")
            return embedding_list
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except requests.RequestException as e:
        logger.error(f"Failed to download image from URL {image_url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Face extraction from URL failed: {str(e)}")
        return None


def compare_face_encodings(encoding1, encoding2, threshold=0.6):
    """
    Compare two face encodings and return similarity score.
    Returns True if faces match (distance < threshold), False otherwise.
    """
    try:
        if not encoding1 or not encoding2:
            return False
        
        # Convert to numpy arrays
        enc1 = np.array(encoding1)
        enc2 = np.array(encoding2)
        
        # Calculate Euclidean distance
        distance = np.linalg.norm(enc1 - enc2)
        
        logger.info(f"Face comparison distance: {distance:.4f} (threshold: {threshold})")
        return distance < threshold
        
    except Exception as e:
        logger.error(f"Face comparison error: {str(e)}")
        return False



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
                    

                    # Extract face encoding from uploaded image
                    try:
                        face_encoding = extract_face_encoding_from_url(user.profile_image, str(user.id))
                        if face_encoding:
                            # Check if user already has face encoding
                            if user.face_encoding:
                                # Compare with existing encoding
                                if compare_face_encodings(user.face_encoding, face_encoding):
                                    logger.info(f"Profile image matches existing face encoding for user: {user.username}")
                                else:
                                    logger.warning(f"Profile image does not match existing face encoding for user: {user.username}")
                            
                            # Update face encoding with profile image
                            user.face_encoding = face_encoding
                            logger.info(f"Face encoding extracted and updated from profile image for user: {user.username}")
                        else:
                            logger.info(f"No face detected in profile image for user: {user.username}")
                    except Exception as face_error:
                        logger.error(f"Face encoding extraction failed: {str(face_error)}")
                        # Continue without failing the profile update
                    

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



class GoogleLoginInitiateView(APIView):
    """
    Initiate Google OAuth flow
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Get Google OAuth credentials from environment
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
            redirect_uri = os.environ.get('GOOGLE_CALLBACK_URL')
            
            if not client_id or not redirect_uri:
                return Response({
                    'error': 'Google OAuth is not configured properly'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Build OAuth URL
            params = {
                'client_id': client_id,
                'redirect_uri': redirect_uri,
                'response_type': 'code',
                'scope': 'openid email profile',
                'access_type': 'offline',
                'prompt': 'consent'
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            
            return Response({
                'auth_url': auth_url
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Google login initiate error: {str(e)}")
            return Response({
                'error': 'Failed to initiate Google login'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GoogleCallbackView(APIView):
    """
    Handle Google OAuth callback
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get authorization code from request
            code = request.data.get('code')
            
            if not code:
                return Response({
                    'error': 'Authorization code is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get Google OAuth credentials from environment
            client_id = os.environ.get('GOOGLE_CLIENT_ID')
            client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
            redirect_uri = os.environ.get('GOOGLE_CALLBACK_URL')
            
            if not all([client_id, client_secret, redirect_uri]):
                return Response({
                    'error': 'Google OAuth is not configured properly'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Create flow instance
            flow = Flow.from_client_config(
                client_config={
                    'web': {
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                        'token_uri': 'https://oauth2.googleapis.com/token',
                        'redirect_uris': [redirect_uri]
                    }
                },
                scopes=['openid', 'email', 'profile'],
                redirect_uri=redirect_uri
            )
            
            # Exchange authorization code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Verify the ID token
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                client_id
            )
            
            # Extract user info
            email = id_info.get('email')
            first_name = id_info.get('given_name', '')
            last_name = id_info.get('family_name', '')
            google_id = id_info.get('sub')
            picture = id_info.get('picture', '')
            
            if not email:
                return Response({
                    'error': 'Email not provided by Google'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                
                # Update auth_provider if it's not set
                if not user.auth_provider or user.auth_provider == 'email':
                    user.auth_provider = 'google'
                    user.google_id = google_id
                    user.is_verified = True
                    if picture and not user.profile_picture:
                        user.profile_picture = picture
                    user.save()
                    
                logger.info(f"Existing user logged in with Google: {email}")
                
            except DoesNotExist:
                # Create new user
                user = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    username=email.split('@')[0],  # Use email prefix as username
                    auth_provider='google',
                    google_id=google_id,
                    is_verified=True,  # Google accounts are pre-verified
                    profile_picture=picture if picture else None
                )
                
                # Set a random password (won't be used for Google auth)
                import secrets
                user.set_password(secrets.token_urlsafe(32))
                user.save()
                
                logger.info(f"New user created with Google: {email}")
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Prepare user data
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'profile_picture': user.profile_picture,
                'auth_provider': user.auth_provider,
                'is_verified': user.is_verified,
                'face_registered': user.face_encoding is not None and len(user.face_encoding) > 0
            }
            
            return Response({
                'message': 'Login successful',
                'user': user_data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Google callback error: {str(e)}")
            return Response({
                'error': f'Google authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterFaceView(APIView):
    """
    Register user's face for facial recognition login
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get base64 encoded image from request
            image_data = request.data.get('image')
            
            if not image_data:
                return Response({
                    'error': 'Image data is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Remove data URL prefix if present
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Save temporarily
                temp_path = f'temp_face_{request.user.id}.jpg'
                image.save(temp_path)
                
                logger.info(f"Processing face image for user: {request.user.email}")
                
                # Extract face embedding using DeepFace
                try:
                    # DeepFace will detect face and extract embedding
                    # Try multiple detectors in order of preference
                    detectors = ['retinaface', 'mtcnn', 'opencv', 'ssd']
                    embedding_objs = None
                    
                    for detector in detectors:
                        try:
                            embedding_objs = DeepFace.represent(
                                img_path=temp_path,
                                model_name='Facenet',
                                enforce_detection=True,
                                detector_backend=detector,
                                align=True
                            )
                            if embedding_objs and len(embedding_objs) > 0:
                                logger.info(f"Face detected successfully using {detector}")
                                break
                        except Exception as detector_error:
                            logger.warning(f"Detector {detector} failed: {str(detector_error)}")
                            continue
                    
                    if not embedding_objs or len(embedding_objs) == 0:
                        os.remove(temp_path)
                        return Response({
                            'error': 'No face detected in the image. Please ensure your face is clearly visible and well-lit.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    # Get the first face embedding
                    embedding = embedding_objs[0]['embedding']
                    
                    # Convert numpy array to list for MongoDB storage
                    embedding_list = [float(x) for x in embedding]
                    
                    # Update user's face encoding (webcam only - no profile image comparison)
                    user = request.user
                    user.face_encoding = embedding_list
                    user.save()
                    
                    logger.info(f"Face registered successfully for user: {user.email}")
                    logger.info(f"Face encoding length: {len(embedding_list)}")
                    logger.info(f"Face encoding sample: {embedding_list[:5]}...")
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    
                    return Response({
                        'message': 'Face registered successfully! You can now login using facial recognition.',
                        'face_registered': True
                    }, status=status.HTTP_200_OK)
                    
                except ValueError as e:
                    # No face detected
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    logger.error(f"Face detection error: {str(e)}")
                    return Response({
                        'error': 'No face detected in the image. Please try again with a clear photo of your face.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Image processing error: {str(e)}")
                return Response({
                    'error': 'Invalid image data. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Register face error: {str(e)}")
            return Response({
                'error': 'Failed to register face. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterFaceFromProfileView(APIView):
    """
    Register user's face for facial recognition using their profile image
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            user = request.user
            
            if not user.profile_image:
                return Response({
                    'error': 'No profile image found. Please upload a profile image first.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Extracting face encoding from profile image for user: {user.email}")
            
            # Extract face encoding from profile image
            face_encoding = extract_face_encoding_from_url(user.profile_image, str(user.id))
            
            if not face_encoding:
                return Response({
                    'error': 'No face detected in your profile image. Please upload a clear photo with your face visible.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update user's face encoding
            user.face_encoding = face_encoding
            user.save()
            
            logger.info(f"Face registered from profile image for user: {user.email}")
            
            return Response({
                'message': 'Face registered successfully from your profile image! You can now login using facial recognition.',
                'face_registered': True
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Register face from profile error: {str(e)}")
            return Response({
                'error': 'Failed to register face from profile image. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceLoginView(APIView):
    """
    Login user using facial recognition
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get base64 encoded image from request
            image_data = request.data.get('image')
            
            if not image_data:
                return Response({
                    'error': 'Image data is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Remove data URL prefix if present
            if 'base64,' in image_data:
                image_data = image_data.split('base64,')[1]
            
            # Decode base64 image
            try:
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Save temporarily
                temp_path = f'temp_login_{int(timezone.now().timestamp())}.jpg'
                image.save(temp_path)
                
                logger.info("Processing face login attempt")
                
                # Extract face embedding
                try:
                    # Try multiple detectors in order of preference
                    detectors = ['retinaface', 'mtcnn', 'opencv', 'ssd']
                    embedding_objs = None
                    
                    for detector in detectors:
                        try:
                            embedding_objs = DeepFace.represent(
                                img_path=temp_path,
                                model_name='Facenet',
                                enforce_detection=True,
                                detector_backend=detector,
                                align=True
                            )
                            if embedding_objs and len(embedding_objs) > 0:
                                logger.info(f"Face detected successfully using {detector}")
                                break
                        except Exception as detector_error:
                            logger.warning(f"Detector {detector} failed: {str(detector_error)}")
                            continue
                    
                    if not embedding_objs or len(embedding_objs) == 0:
                        os.remove(temp_path)
                        return Response({
                            'error': 'No face detected. Please ensure your face is clearly visible and well-lit.'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    login_embedding = embedding_objs[0]['embedding']
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    
                    # Get all users with face encodings (webcam registered only)
                    # Use proper MongoDB query to find users with non-null face encodings
                    users_with_faces = []
                    for user in User.objects.all():
                        if user.face_encoding and len(user.face_encoding) == 128:
                            users_with_faces.append(user)
                    
                    logger.info(f"Found {len(users_with_faces)} users with valid face encodings")
                    
                    if not users_with_faces:
                        return Response({
                            'error': 'No registered faces found. Please register your face first in your profile.',
                            'debug_info': {
                                'users_with_faces': 0,
                                'message': 'No face encodings available'
                            }
                        }, status=status.HTTP_404_NOT_FOUND)
                    
                    # Improved matching: normalize embeddings, use cosine similarity with Euclidean fallback
                    best_match = None
                    best_similarity = -1.0  # higher is better for cosine
                    min_distance = float('inf')
                    # Thresholds (tune as needed)
                    cos_threshold = 0.50   # cosine similarity threshold (0..1)
                    euclid_threshold = 0.65  # euclidean distance threshold

                    logger.info(f"Checking {len(users_with_faces)} users with face encodings (using cosine similarity)")

                    # Log all comparison results for debugging
                    logger.info(f"🔍 FACE COMPARISON RESULTS for {len(users_with_faces)} registered users:")
                    for user in users_with_faces:
                        try:
                            if not user.face_encoding:
                                continue
                            stored_embedding = np.array(user.face_encoding, dtype=np.float32)
                            login_array = np.array(login_embedding, dtype=np.float32)
                            if stored_embedding.shape != login_array.shape:
                                logger.warning(f"Shape mismatch for {user.email}: stored={stored_embedding.shape}, current={login_array.shape}")
                                continue

                            # Cosine similarity
                            cos_sim = float(np.dot(stored_embedding, login_array) / (np.linalg.norm(stored_embedding) * np.linalg.norm(login_array)))
                            # Euclidean distance
                            euclid_dist = float(np.linalg.norm(stored_embedding - login_array))

                            logger.info(f"  {user.email}: cosine={cos_sim:.4f}, euclidean={euclid_dist:.4f}")
                        except Exception as comp_err:
                            logger.error(f"Comparison error for {user.email}: {str(comp_err)}")
                            continue

                    # Normalize current embedding once
                    current_embedding = np.array(login_embedding, dtype=np.float32)
                    try:
                        current_norm = np.linalg.norm(current_embedding)
                        if current_norm == 0 or not np.isfinite(current_norm):
                            logger.error("Current embedding has invalid norm")
                            current_embedding = current_embedding
                            current_norm = 1.0
                        current_unit = current_embedding / current_norm
                    except Exception as norm_err:
                        logger.error(f"Failed to normalize current embedding: {str(norm_err)}")
                        current_unit = current_embedding

                    for user in users_with_faces:
                        if not user.face_encoding:
                            logger.debug(f"Skipping user {user.email}: no face_encoding")
                            continue

                        try:
                            stored_embedding = np.array(user.face_encoding, dtype=np.float32)

                            # Check shapes
                            if stored_embedding.shape != current_embedding.shape:
                                logger.warning(f"Shape mismatch for user {user.email}: stored={stored_embedding.shape}, current={current_embedding.shape}")
                                continue

                            # Normalize stored embedding
                            stored_norm = np.linalg.norm(stored_embedding)
                            if stored_norm == 0 or not np.isfinite(stored_norm):
                                logger.warning(f"Stored embedding invalid norm for {user.email}")
                                continue
                            stored_unit = stored_embedding / stored_norm

                            # Cosine similarity (dot product of unit vectors)
                            cosine_sim = float(np.dot(stored_unit, current_unit))

                            # Euclidean distance for extra info
                            distance = float(np.linalg.norm(stored_embedding - current_embedding))

                            logger.info(f"User {user.email}: cosine={cosine_sim:.4f}, distance={distance:.4f}")

                            # Prefer cosine similarity, but enforce minimum distance sanity
                            if np.isfinite(cosine_sim) and cosine_sim > best_similarity:
                                best_similarity = cosine_sim
                                best_match_candidate = user
                                candidate_distance = distance

                        except Exception as user_error:
                            logger.error(f"Error processing user {user.email}: {str(user_error)}")
                            continue

                    # Decide final match using thresholds
                    if best_similarity >= cos_threshold:
                        best_match = best_match_candidate
                        min_distance = candidate_distance if 'candidate_distance' in locals() else min_distance
                        logger.info(f"✅ MATCH FOUND: {best_match.email} (cosine={best_similarity:.4f}, distance={min_distance:.4f})")
                        match_method = 'cosine'
                    else:
                        # As fallback, try a euclidean-based pass to find any very-close matches
                        logger.info("No candidate passed cosine threshold, performing euclidean fallback check")
                        best_match = None  # Reset for fallback
                        min_distance = float('inf')
                        for user in users_with_faces:
                            try:
                                if not user.face_encoding:
                                    continue
                                stored_embedding = np.array(user.face_encoding, dtype=np.float32)
                                if stored_embedding.shape != current_embedding.shape:
                                    continue
                                distance = float(np.linalg.norm(stored_embedding - current_embedding))
                                if distance < min_distance and distance <= euclid_threshold:
                                    min_distance = distance
                                    best_match = user
                            except Exception as eu_err:
                                logger.error(f"Euclidean fallback error for {user.email}: {str(eu_err)}")
                                continue

                        if best_match:
                            logger.info(f"✅ MATCH FOUND (fallback): {best_match.email} (distance={min_distance:.4f})")
                            match_method = 'euclidean_fallback'
                        else:
                            logger.warning(f"❌ NO MATCH FOUND: best_similarity={best_similarity:.4f}, min_distance={min_distance if min_distance!=float('inf') else 'inf'}")
                            match_method = 'none'
                    
                    if best_match:
                        # Update last login
                        best_match.last_login = timezone.now()
                        best_match.save()
                        
                        # Generate JWT tokens
                        refresh = RefreshToken.for_user(best_match)
                        
                        # Prepare user data
                        user_data = {
                            'id': str(best_match.id),
                            'email': best_match.email,
                            'first_name': best_match.first_name,
                            'last_name': best_match.last_name,
                            'username': best_match.username,
                            'profile_image': best_match.profile_image,
                            'role': best_match.role,
                            'is_verified': best_match.is_verified,
                            'face_registered': best_match.face_encoding is not None and len(best_match.face_encoding) > 0
                        }
                        
                        # Determine which metric matched
                        used_method = 'euclidean'
                        confidence = None
                        if best_similarity >= cos_threshold:
                            used_method = 'cosine'
                            confidence = round(float(best_similarity), 4)
                        else:
                            # Convert euclidean distance into a rough confidence (0..1)
                            try:
                                confidence = max(0.0, 1.0 - (min_distance / euclid_threshold))
                                confidence = round(float(confidence), 4)
                            except Exception:
                                confidence = None

                        logger.info(f"Face login successful for user: {best_match.email} (method={used_method}, distance: {min_distance:.4f}, cosine={best_similarity:.4f})")

                        return Response({
                            'message': 'Face login successful!',
                            'user': user_data,
                            'tokens': {
                                'access': str(refresh.access_token),
                                'refresh': str(refresh)
                            },
                            'match_info': {
                                'method': used_method,
                                'cosine': round(float(best_similarity), 4),
                                'distance': round(min_distance, 4),
                                'confidence': confidence
                            }
                        }, status=status.HTTP_200_OK)
                    else:
                        logger.warning(f"No matching face found (best_similarity={best_similarity:.4f}, min_distance={min_distance if min_distance!=float('inf') else 'inf'})")

                        # Handle infinity values for JSON serialization
                        best_distance_json = 999.0 if min_distance == float('inf') else round(min_distance, 4)

                        return Response({
                            'error': f'Face not recognized. Please register your face first or use email/password login.',
                            'debug_info': {
                                'best_distance': best_distance_json,
                                'cos_threshold': cos_threshold,
                                'euclid_threshold': euclid_threshold,
                                'users_checked': len(users_with_faces),
                                'message': 'No matching face found'
                            }
                        }, status=status.HTTP_401_UNAUTHORIZED)
                        
                except ValueError as e:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    logger.error(f"Face detection error: {str(e)}")
                    return Response({
                        'error': 'No face detected. Please try again with a clear photo.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Image processing error: {str(e)}")
                return Response({
                    'error': 'Invalid image data. Please try again.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Face login error: {str(e)}")
            return Response({
                'error': 'Face login failed. Please try again or use email/password login.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """
    Logout user by blacklisting the refresh token
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get refresh token from request
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                try:
                    # Blacklist the refresh token
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.warning(f"Token blacklisting failed: {str(e)}")
            
            return Response({
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FaceDebugView(APIView):
    """
    Debug endpoint to check face recognition database status
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:
            # Get statistics
            total_users = User.objects.count()
            users_with_faces = User.objects(face_encoding__exists=True, face_encoding__ne=None).count()
            users_with_images = User.objects(profile_image__exists=True, profile_image__ne=None).count()
            
            # Get list of users with faces (without showing actual encodings)
            users_list = []
            for user in User.objects(face_encoding__exists=True, face_encoding__ne=None):
                users_list.append({
                    'email': user.email,
                    'username': user.username,
                    'face_encoding_length': len(user.face_encoding) if user.face_encoding else 0,
                    'has_profile_image': bool(user.profile_image)
                })
            
            return Response({
                'total_users': total_users,
                'users_with_faces': users_with_faces,
                'users_with_images': users_with_images,
                'users_with_face_encodings': users_list,
                'status': 'active'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Face debug error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve debug information'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """
        Test face comparison between two images
        """
        try:
            # Get two base64 images from request
            image1_data = request.data.get('image1')
            image2_data = request.data.get('image2')
            
            if not image1_data or not image2_data:
                return Response({
                    'error': 'Both image1 and image2 are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process both images
            results = {}
            for img_key, img_data in [('image1', image1_data), ('image2', image2_data)]:
                # Remove data URL prefix if present
                if 'base64,' in img_data:
                    img_data = img_data.split('base64,')[1]
                
                # Decode and save temporarily
                image_bytes = base64.b64decode(img_data)
                image = Image.open(io.BytesIO(image_bytes))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                temp_path = f'temp_debug_{img_key}_{int(timezone.now().timestamp())}.jpg'
                image.save(temp_path)
                
                # Extract face embedding
                try:
                    embedding_objs = DeepFace.represent(
                        img_path=temp_path,
                        model_name='Facenet',
                        enforce_detection=True,
                        detector_backend='retinaface',
                        align=True
                    )
                    
                    if embedding_objs and len(embedding_objs) > 0:
                        results[img_key] = {
                            'embedding': embedding_objs[0]['embedding'],
                            'success': True
                        }
                    else:
                        results[img_key] = {'success': False, 'error': 'No face detected'}
                        
                except Exception as e:
                    results[img_key] = {'success': False, 'error': str(e)}
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            # Compare the embeddings if both successful
            comparison = {}
            if results.get('image1', {}).get('success') and results.get('image2', {}).get('success'):
                emb1 = np.array(results['image1']['embedding'], dtype=np.float32)
                emb2 = np.array(results['image2']['embedding'], dtype=np.float32)
                
                # Cosine similarity
                cos_sim = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
                
                # Euclidean distance
                euclid_dist = float(np.linalg.norm(emb1 - emb2))
                
                comparison = {
                    'cosine_similarity': round(cos_sim, 4),
                    'euclidean_distance': round(euclid_dist, 4),
                    'same_person_likelihood': 'High' if cos_sim > 0.5 else 'Low',
                    'threshold_cos': 0.50,
                    'threshold_euclid': 0.65
                }
            
            return Response({
                'image1_result': results.get('image1', {}),
                'image2_result': results.get('image2', {}),
                'comparison': comparison,
                'message': 'Face comparison test completed'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Face debug test error: {str(e)}")
            return Response({
                'error': 'Face comparison test failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateProfileBioView(APIView):
    """
    Generate AI-powered profile bio for the authenticated user
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user

            # Generate bio using AI service
            bio = user_ai_service.generate_profile_bio(user)

            return Response({
                'message': 'Profile bio generated successfully',
                'bio': bio
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Generate profile bio error: {str(e)}")
            return Response({
                'error': 'Failed to generate profile bio. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyzeArtworkView(APIView):
    """
    Analyze user's artwork using AI and provide enhanced description, tags, and style
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            artwork_title = request.data.get('title', '').strip()
            artwork_description = request.data.get('description', '').strip()

            if not artwork_title:
                return Response({
                    'error': 'Artwork title is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Analyze artwork using AI service
            analysis = user_ai_service.analyze_user_artwork(
                user=user,
                artwork_title=artwork_title,
                artwork_description=artwork_description
            )

            return Response({
                'message': 'Artwork analyzed successfully',
                'analysis': analysis
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Analyze artwork error: {str(e)}")
            return Response({
                'error': 'Failed to analyze artwork. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateRecommendationsView(APIView):
    """
    Generate personalized artwork recommendations based on user's profile
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user

            # Generate recommendations using AI service
            recommendations = user_ai_service.generate_personalized_recommendations(user)

            return Response({
                'message': 'Recommendations generated successfully',
                'recommendations': recommendations
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Generate recommendations error: {str(e)}")
            return Response({
                'error': 'Failed to generate recommendations. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



