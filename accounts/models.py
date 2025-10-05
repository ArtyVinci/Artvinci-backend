"""
MongoEngine models for Artvinci application.
These models use MongoDB directly via MongoEngine.
"""

from mongoengine import Document, fields, CASCADE
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta, datetime
import random


class User(Document):
    """
    MongoEngine User Document for storing user data in MongoDB.
    """
    
    ROLE_CHOICES = ('admin', 'artist', 'visitor')
    
    # Authentication fields
    username = fields.StringField(required=True, unique=True, max_length=150)
    email = fields.EmailField(required=True, unique=True)
    password = fields.StringField(required=True)
    
    # Profile fields
    first_name = fields.StringField(max_length=150, default='')
    last_name = fields.StringField(max_length=150, default='')
    role = fields.StringField(max_length=10, choices=ROLE_CHOICES, default='visitor')
    bio = fields.StringField(default='')
    profile_image = fields.StringField(default=None, null=True)  # Cloudinary URL
    
    # Account status
    is_active = fields.BooleanField(default=True)
    is_verified = fields.BooleanField(default=False)
    is_staff = fields.BooleanField(default=False)
    is_superuser = fields.BooleanField(default=False)
    
    # Timestamps
    date_joined = fields.DateTimeField(default=timezone.now)
    last_login = fields.DateTimeField(default=None, null=True)
    
    # Reserved for future features
    face_encoding = fields.BinaryField(default=None, null=True)
    
    meta = {
        'collection': 'users',
        'indexes': [
            {'fields': ['email'], 'unique': True},
            {'fields': ['username'], 'unique': True}
        ]
    }
    
    def set_password(self, raw_password):
        """Hash and set the user's password."""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Verify a password against the stored hash."""
        return check_password(raw_password, self.password)
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @property
    def is_authenticated(self):
        """
        Always return True for authenticated users.
        This is required by Django REST Framework's IsAuthenticated permission.
        """
        return True
    
    @property
    def is_anonymous(self):
        """
        Always return False for authenticated users.
        This is required by Django REST Framework.
        """
        return False
    
    @property
    def profile_image_url(self):
        """Return the profile image URL."""
        return self.profile_image if self.profile_image else None
    
    def to_dict(self):
        """Convert document to dictionary for serialization."""
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'bio': self.bio,
            'profile_image': self.profile_image_url,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class EmailVerificationOTP(Document):
    """
    MongoEngine Document for storing OTP codes for email verification.
    Codes expire after 10 minutes.
    """
    user = fields.ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    code = fields.StringField(required=True, max_length=6)
    created_at = fields.DateTimeField(default=timezone.now)
    expires_at = fields.DateTimeField(required=True)
    is_used = fields.BooleanField(default=False)
    
    meta = {
        'collection': 'email_verification_otp',
        'indexes': [
            'user',
            'code',
            {'fields': ['expires_at'], 'expireAfterSeconds': 0}  # Auto-delete expired documents
        ]
    }
    
    @staticmethod
    def generate_code():
        """Generate a random 6-digit OTP code."""
        return str(random.randint(100000, 999999))
    
    def is_expired(self):
        """Check if the OTP code has expired."""
        now = timezone.now()
        # Ensure both datetimes are timezone-aware
        if self.expires_at.tzinfo is None:
            # If expires_at is naive, make it aware using default timezone
            from django.utils.timezone import make_aware
            expires_at_aware = make_aware(self.expires_at)
        else:
            expires_at_aware = self.expires_at
        return now > expires_at_aware
    
    def is_valid(self):
        """Check if the OTP is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired()
    
    def __str__(self):
        return f"OTP for {self.user.email}: {self.code}"
    
    @classmethod
    def create_for_user(cls, user):
        """Create a new OTP for a user."""
        code = cls.generate_code()
        now = timezone.now()
        expires_at = now + timedelta(minutes=10)
        
        # Ensure timezone-aware datetime
        if expires_at.tzinfo is None:
            from django.utils.timezone import make_aware
            expires_at = make_aware(expires_at)
        
        # Deactivate any existing unused OTPs for this user
        cls.objects(user=user, is_used=False).update(is_used=True)
        
        # Create new OTP
        otp = cls(
            user=user,
            code=code,
            expires_at=expires_at
        )
        otp.save()
        return otp


class PasswordResetToken(Document):
    """
    MongoEngine Document for storing password reset tokens.
    Tokens expire after 1 hour.
    """
    user = fields.ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    token = fields.StringField(required=True, unique=True, max_length=64)
    created_at = fields.DateTimeField(default=timezone.now)
    expires_at = fields.DateTimeField(required=True)
    is_used = fields.BooleanField(default=False)
    
    meta = {
        'collection': 'password_reset_tokens',
        'indexes': [
            'user',
            'token',
            {'fields': ['expires_at'], 'expireAfterSeconds': 0}  # Auto-delete expired documents
        ]
    }
    
    @staticmethod
    def generate_token():
        """Generate a random secure token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        """Check if the token has expired."""
        now = timezone.now()
        # Ensure both datetimes are timezone-aware
        if self.expires_at.tzinfo is None:
            from django.utils.timezone import make_aware
            expires_at_aware = make_aware(self.expires_at)
        else:
            expires_at_aware = self.expires_at
        return now > expires_at_aware
    
    def is_valid(self):
        """Check if the token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired()
    
    def __str__(self):
        return f"Password Reset Token for {self.user.email}"
    
    @classmethod
    def create_for_user(cls, user):
        """Create a new password reset token for a user."""
        token = cls.generate_token()
        now = timezone.now()
        expires_at = now + timedelta(hours=1)
        
        # Ensure timezone-aware datetime
        if expires_at.tzinfo is None:
            from django.utils.timezone import make_aware
            expires_at = make_aware(expires_at)
        
        # Deactivate any existing unused tokens for this user
        cls.objects(user=user, is_used=False).update(is_used=True)
        
        # Create new token
        reset_token = cls(
            user=user,
            token=token,
            expires_at=expires_at
        )
        reset_token.save()
        return reset_token
