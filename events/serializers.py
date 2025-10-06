"""
Serializers for Event documents using MongoEngine.
"""

from rest_framework import serializers
from django.utils.text import slugify
from django.utils import timezone
from .models import Event, EventSubscription, EventImage


class EventImageSerializer(serializers.Serializer):
    """Serializer for EventImage embedded document"""
    url = serializers.URLField(required=True)
    public_id = serializers.CharField(required=True)
    caption = serializers.CharField(max_length=200, required=False, default='')
    is_primary = serializers.BooleanField(default=False)
    uploaded_at = serializers.DateTimeField(read_only=True)


class ArtistBasicSerializer(serializers.Serializer):
    """Basic artist information for event listing"""
    id = serializers.CharField(read_only=True)
    username = serializers.CharField(read_only=True)
    profile_image = serializers.CharField(read_only=True, allow_null=True)


class EventListSerializer(serializers.Serializer):
    """Serializer for event list view (lighter data)"""
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    short_description = serializers.CharField(read_only=True)
    artist = ArtistBasicSerializer(read_only=True)
    category = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    location_name = serializers.CharField(read_only=True)
    location_city = serializers.CharField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    cover_image = serializers.CharField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    ticket_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    max_attendees = serializers.IntegerField(read_only=True)
    current_attendees = serializers.IntegerField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    # Removed is_upcoming, is_ongoing, is_past to avoid timezone comparison errors
    # is_upcoming = serializers.BooleanField(read_only=True)
    # is_ongoing = serializers.BooleanField(read_only=True)
    # is_past = serializers.BooleanField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True, allow_null=True)
    registration_open = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def to_representation(self, instance):
        """Convert MongoEngine document to dict"""
        if isinstance(instance, Event):
            return instance.to_dict()
        return super().to_representation(instance)


class EventDetailSerializer(serializers.Serializer):
    """Serializer for event detail view (complete data)"""
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    short_description = serializers.CharField(read_only=True)
    artist = ArtistBasicSerializer(read_only=True)
    category = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)
    registration_deadline = serializers.DateTimeField(read_only=True, allow_null=True)
    location = serializers.DictField(read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    online_link = serializers.URLField(read_only=True, allow_null=True, allow_blank=True)
    max_attendees = serializers.IntegerField(read_only=True)
    current_attendees = serializers.IntegerField(read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    ticket_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    images = EventImageSerializer(many=True, read_only=True)
    cover_image = serializers.CharField(read_only=True)
    tags = serializers.ListField(child=serializers.CharField(), read_only=True)
    requirements = serializers.CharField(read_only=True)
    schedule = serializers.CharField(read_only=True)
    featured_artists = serializers.ListField(child=serializers.CharField(), read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    views_count = serializers.IntegerField(read_only=True)
    # Removed is_upcoming, is_ongoing, is_past to avoid timezone comparison errors
    # is_upcoming = serializers.BooleanField(read_only=True)
    # is_ongoing = serializers.BooleanField(read_only=True)
    # is_past = serializers.BooleanField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True, allow_null=True)
    registration_open = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    published_at = serializers.DateTimeField(read_only=True, allow_null=True)
    
    def to_representation(self, instance):
        """Convert MongoEngine document to dict"""
        if isinstance(instance, Event):
            return instance.to_dict()
        return super().to_representation(instance)


class EventCreateUpdateSerializer(serializers.Serializer):
    """Serializer for creating and updating events"""
    title = serializers.CharField(required=True, max_length=200)
    description = serializers.CharField(required=True)
    short_description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=Event.CATEGORY_CHOICES, default='exhibition')
    status = serializers.ChoiceField(choices=Event.STATUS_CHOICES, default='draft')
    
    # Date & Time
    start_date = serializers.DateTimeField(required=True)
    end_date = serializers.DateTimeField(required=True)
    registration_deadline = serializers.DateTimeField(required=False, allow_null=True)
    
    # Location
    location_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    location_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    location_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    location_country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=20, decimal_places=15, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=20, decimal_places=15, required=False, allow_null=True)
    is_online = serializers.BooleanField(default=False)
    online_link = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    
    # Capacity & Pricing
    max_attendees = serializers.IntegerField(default=0, min_value=0)
    is_free = serializers.BooleanField(default=True)
    ticket_price = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    currency = serializers.CharField(max_length=3, default='USD')
    
    # Additional
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)
    requirements = serializers.CharField(required=False, allow_blank=True)
    schedule = serializers.CharField(required=False, allow_blank=True)
    featured_artists = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    
    def validate(self, attrs):
        """Validate event data"""
        # Ensure end_date is after start_date
        if attrs.get('end_date') and attrs.get('start_date'):
            if attrs['end_date'] < attrs['start_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        # Ensure registration deadline is before start date
        if attrs.get('registration_deadline') and attrs.get('start_date'):
            if attrs['registration_deadline'] > attrs['start_date']:
                raise serializers.ValidationError({
                    'registration_deadline': 'Registration deadline must be before event start date'
                })
        
        # If not free, ticket price must be > 0
        if not attrs.get('is_free', True) and attrs.get('ticket_price', 0) <= 0:
            raise serializers.ValidationError({
                'ticket_price': 'Ticket price must be greater than 0 for paid events'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create new event"""
        # Artist will be set in the view before save
        event = Event(**validated_data)
        # Don't save here - let the view set artist first
        # event.save() will be called in the view after setting artist
        return event
    
    def update(self, instance, validated_data):
        """Update existing event"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class EventSubscriptionSerializer(serializers.Serializer):
    """Serializer for event subscriptions"""
    id = serializers.CharField(read_only=True)
    event = EventListSerializer(read_only=True)
    user = ArtistBasicSerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    confirmation_code = serializers.CharField(read_only=True)
    attendee_notes = serializers.CharField(required=False, allow_blank=True)
    special_requirements = serializers.CharField(required=False, allow_blank=True)
    payment_status = serializers.CharField(read_only=True)
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subscribed_at = serializers.DateTimeField(read_only=True)
    confirmed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    
    def to_representation(self, instance):
        """Convert MongoEngine document to dict"""
        if isinstance(instance, EventSubscription):
            return instance.to_dict()
        return super().to_representation(instance)


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating event subscription"""
    attendee_name = serializers.CharField(required=True, max_length=200, help_text="Name of the person attending")
    attendee_notes = serializers.CharField(required=False, allow_blank=True, default='')
    special_requirements = serializers.CharField(required=False, allow_blank=True, default='')
    payment_method = serializers.ChoiceField(choices=['cash', 'online'], default='cash', help_text="Payment method: cash or online")
    
    def validate(self, attrs):
        """Validate subscription data"""
        # Ensure attendee_name is provided
        if not attrs.get('attendee_name', '').strip():
            raise serializers.ValidationError({
                'attendee_name': 'Attendee name is required'
            })
        return attrs
