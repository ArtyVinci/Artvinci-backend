"""
Serializers for MongoEngine User documents.
"""

from rest_framework import serializers
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, EmailVerificationOTP


class UserSerializer(serializers.Serializer):
    """Serializer for reading user profile"""
    
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    bio = serializers.CharField(read_only=True)
    profile_image_url = serializers.CharField(read_only=True, source='profile_image')
    is_verified = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        """Convert MongoEngine document to dict"""
        if isinstance(instance, User):
            return instance.to_dict()
        return super().to_representation(instance)


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    
    username = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=False,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=False, allow_blank=True, default='')
    last_name = serializers.CharField(required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=['admin', 'artist', 'visitor'], default='visitor')
    bio = serializers.CharField(required=False, allow_blank=True, default='')
    profile_image = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    def validate_email(self, value):
        """Check that email is not already used"""
        email_lower = value.lower()
        if User.objects(email=email_lower).first():
            raise serializers.ValidationError("A user with this email already exists.")
        return email_lower
    
    def validate_username(self, value):
        """Check that username is not already taken"""
        if User.objects(username=value).first():
            raise serializers.ValidationError("This username is already taken.")
        return value
    
    def validate(self, attrs):
        """Global validation: check passwords match"""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password_confirm and password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create a new user with hashed password"""
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.is_verified = False  # Require email verification
        user.save()
        
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate credentials and return user"""
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        # Check if user exists
        user = User.objects(email=email).first()
        
        if not user:
            raise serializers.ValidationError({
                'email': "No account found with this email address."
            })
        
        # Check if account is active
        if not user.is_active:
            raise serializers.ValidationError({
                'email': "This account has been deactivated."
            })
        
        # Verify password
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': "Incorrect password."
            })
        
        # Check if email is verified
        if not user.is_verified:
            raise serializers.ValidationError({
                'email': "Please verify your email address before logging in."
            })
        
        attrs['user'] = user
        return attrs


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for OTP verification"""
    
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, max_length=6, min_length=6)
    
    def validate(self, attrs):
        """Validate OTP code"""
        email = attrs.get('email', '').lower()
        code = attrs.get('code')
        
        # Find user
        user = User.objects(email=email).first()
        if not user:
            raise serializers.ValidationError({
                'email': "User not found."
            })
        
        # Find valid OTP
        otp = EmailVerificationOTP.objects(
            user=user,
            code=code,
            is_used=False
        ).first()
        
        if not otp:
            raise serializers.ValidationError({
                'code': "Invalid verification code."
            })
        
        if otp.is_expired():
            raise serializers.ValidationError({
                'code': "This verification code has expired."
            })
        
        attrs['user'] = user
        attrs['otp'] = otp
        return attrs


class SendOTPSerializer(serializers.Serializer):
    """Serializer for sending OTP"""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check that user exists"""
        email_lower = value.lower()
        user = User.objects(email=email_lower).first()
        
        if not user:
            raise serializers.ValidationError("No account found with this email address.")
        
        return email_lower


def get_tokens_for_user(user):
    """
    Generate JWT tokens for a user.
    Since we're using MongoEngine, we need to create a dict representation.
    """
    # Create a simple dict with user ID for JWT payload
    user_dict = {
        'id': str(user.id),
        'email': user.email,
        'username': user.username
    }
    
    # Create refresh token with custom claims
    refresh = RefreshToken()
    refresh['user_id'] = str(user.id)
    refresh['email'] = user.email
    refresh['username'] = user.username
    
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }
