"""
Serializers for Sales Management (Ventes)
"""

from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.Serializer):
    """Serializer for order items"""
    artwork_id = serializers.CharField(write_only=True)
    artwork = serializers.SerializerMethodField(read_only=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    def get_artwork(self, obj):
        """Get artwork details"""
        if isinstance(obj, dict):
            return obj.get('artwork')
        
        if hasattr(obj, 'artwork') and obj.artwork:
            return {
                'id': str(obj.artwork.id),
                'title': obj.artwork.title,
                'primary_image': obj.artwork.primary_image,
                'artist': {
                    'id': str(obj.artwork.artist.id),
                    'username': obj.artwork.artist.username,
                } if obj.artwork.artist else None,
            }
        return None


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    items = OrderItemSerializer(many=True)
    shipping_address = serializers.CharField(required=False, allow_blank=True)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """Ensure at least one item"""
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        return value


class OrderSerializer(serializers.Serializer):
    """Serializer for order responses"""
    id = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, read_only=True)
    payment_intent_id = serializers.CharField(read_only=True)
    payment_method = serializers.CharField(read_only=True)
    shipping_address = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
    
    def get_user(self, obj):
        """Get user details"""
        if isinstance(obj, dict):
            return obj.get('user')
        
        if hasattr(obj, 'user') and obj.user:
            return {
                'id': str(obj.user.id),
                'username': obj.user.username,
                'email': obj.user.email,
            }
        return None


class OrderListSerializer(serializers.Serializer):
    """Lightweight serializer for listing orders"""
    id = serializers.CharField(read_only=True)
    user = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def get_user(self, obj):
        """Get user details"""
        if isinstance(obj, dict):
            return obj.get('user')
        
        if hasattr(obj, 'user') and obj.user:
            return {
                'id': str(obj.user.id),
                'username': obj.user.username,
            }
        return None
    
    def get_items_count(self, obj):
        """Get number of items"""
        if isinstance(obj, dict):
            return obj.get('items_count', 0)
        
        if hasattr(obj, 'items'):
            return len(obj.items)
        return 0
