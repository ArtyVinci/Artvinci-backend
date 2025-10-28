"""
Serializers for Artwork management
"""

from rest_framework import serializers
from .models import Artwork, Purchase, ArtworkImage


class ArtworkImageSerializer(serializers.Serializer):
    """Serializer for artwork images"""
    url = serializers.URLField()
    public_id = serializers.CharField(required=False, allow_blank=True)
    caption = serializers.CharField(required=False, allow_blank=True)
    is_primary = serializers.BooleanField(default=False)


class ArtworkListSerializer(serializers.Serializer):
    """Serializer for listing artworks (lightweight)"""
    id = serializers.CharField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.ChoiceField(choices=Artwork.CATEGORY_CHOICES)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    available = serializers.BooleanField()
    is_available = serializers.BooleanField(source='available', read_only=True)
    status = serializers.ChoiceField(choices=Artwork.STATUS_CHOICES, read_only=True)
    primary_image = serializers.URLField(required=False, allow_blank=True)
    artist = serializers.SerializerMethodField()
    views_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def get_artist(self, obj):
        """Get artist basic info"""
        # Handle both dict and object
        if isinstance(obj, dict):
            artist = obj.get('artist')
            if artist and isinstance(artist, dict):
                return {
                    'id': artist.get('id'),
                    'username': artist.get('username'),
                    'profile_image': artist.get('profile_image', ''),
                }
            return None
        
        # Object access
        if hasattr(obj, 'artist') and obj.artist:
            return {
                'id': str(obj.artist.id),
                'username': obj.artist.username,
                'profile_image': getattr(obj.artist, 'profile_image', ''),
            }
        return None


class ArtworkDetailSerializer(serializers.Serializer):
    """Serializer for detailed artwork view"""
    id = serializers.CharField(read_only=True)
    title = serializers.CharField()
    description = serializers.CharField()
    category = serializers.ChoiceField(choices=Artwork.CATEGORY_CHOICES)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    available = serializers.BooleanField()
    status = serializers.ChoiceField(choices=Artwork.STATUS_CHOICES, read_only=True)
    
    primary_image = serializers.URLField(required=False, allow_blank=True)
    images = ArtworkImageSerializer(many=True, required=False)
    
    dimensions = serializers.CharField(required=False, allow_blank=True)
    medium = serializers.CharField(required=False, allow_blank=True)
    year_created = serializers.IntegerField(required=False, allow_null=True)
    
    artist = serializers.SerializerMethodField()
    views_count = serializers.IntegerField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def get_artist(self, obj):
        """Get full artist info"""
        # Handle both dict and object
        if isinstance(obj, dict):
            artist = obj.get('artist')
            if artist and isinstance(artist, dict):
                return artist
            return None
        
        # Object access
        if hasattr(obj, 'artist') and obj.artist:
            return {
                'id': str(obj.artist.id),
                'username': obj.artist.username,
                'email': obj.artist.email,
                'profile_image': getattr(obj.artist, 'profile_image', ''),
                'bio': getattr(obj.artist, 'bio', ''),
            }
        return None


class ArtworkCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating/updating artworks"""
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    category = serializers.ChoiceField(choices=Artwork.CATEGORY_CHOICES)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, default='USD')
    available = serializers.BooleanField(default=True)
    
    # Images will be uploaded separately via Cloudinary
    primary_image = serializers.URLField(required=False, allow_blank=True)
    images = ArtworkImageSerializer(many=True, required=False)
    
    dimensions = serializers.CharField(required=False, allow_blank=True)
    medium = serializers.CharField(required=False, allow_blank=True)
    year_created = serializers.IntegerField(required=False, allow_null=True)
    
    def validate_title(self, value):
        """Validate title"""
        if len(value) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long")
        return value
    
    def validate_price(self, value):
        """Validate price"""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value


class PurchaseSerializer(serializers.Serializer):
    """Serializer for purchase transactions"""
    id = serializers.CharField(read_only=True)
    artwork = ArtworkDetailSerializer(read_only=True)
    artwork_id = serializers.CharField(write_only=True)
    buyer = serializers.SerializerMethodField(read_only=True)
    artist = serializers.SerializerMethodField(read_only=True)
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=Purchase.STATUS_CHOICES, read_only=True)
    
    payment_method = serializers.CharField(required=False, allow_blank=True)
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    
    purchased_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    
    def get_buyer(self, obj):
        if hasattr(obj, 'buyer') and obj.buyer:
            return {
                'id': str(obj.buyer.id),
                'username': obj.buyer.username,
                'email': obj.buyer.email,
            }
        return None
    
    def get_artist(self, obj):
        if hasattr(obj, 'artist') and obj.artist:
            return {
                'id': str(obj.artist.id),
                'username': obj.artist.username,
            }
        return None
