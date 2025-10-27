"""
MongoEngine models for Events in Artvinci application.
Events are created by artists and visitors can subscribe to them.
"""

from mongoengine import Document, EmbeddedDocument, fields, CASCADE
from django.utils import timezone
from datetime import datetime, timedelta
import secrets


class EventImage(EmbeddedDocument):
    """Embedded document for event images"""
    url = fields.StringField(required=True)
    public_id = fields.StringField(required=True)  # Cloudinary public ID
    caption = fields.StringField(max_length=200, default='')
    is_primary = fields.BooleanField(default=False)  # Main event cover image
    uploaded_at = fields.DateTimeField(default=timezone.now)
    
    meta = {
        'ordering': ['-is_primary', '-uploaded_at']
    }


class Event(Document):
    """
    MongoEngine Event Document for storing art events in MongoDB.
    Artists can create events, visitors can subscribe to them.
    """
    
    STATUS_CHOICES = ('draft', 'published', 'ongoing', 'completed', 'cancelled')
    CATEGORY_CHOICES = (
        'exhibition',
        'workshop',
        'gallery_opening',
        'art_fair',
        'auction',
        'performance',
        'artist_talk',
        'networking',
        'competition',
        'other'
    )
    
    # Basic Information
    title = fields.StringField(required=True, max_length=200)
    slug = fields.StringField(required=True, unique=True, max_length=250)
    description = fields.StringField(required=True)
    short_description = fields.StringField(max_length=300, default='')
    
    # Creator (Artist)
    artist = fields.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    
    # Event Details
    category = fields.StringField(choices=CATEGORY_CHOICES, default='exhibition')
    status = fields.StringField(choices=STATUS_CHOICES, default='draft')
    
    # Date & Time
    start_date = fields.DateTimeField(required=True)
    end_date = fields.DateTimeField(required=True)
    registration_deadline = fields.DateTimeField(default=None, null=True)
    
    # Location
    location_name = fields.StringField(max_length=200, default='')
    location_address = fields.StringField(max_length=500, default='')
    location_city = fields.StringField(max_length=100, default='')
    location_country = fields.StringField(max_length=100, default='')
    latitude = fields.DecimalField(precision=15, null=True)  # Precise coordinates for mapping (up to 15 decimal places)
    longitude = fields.DecimalField(precision=15, null=True)
    is_online = fields.BooleanField(default=False)
    online_link = fields.URLField(default='', null=True)
    
    # Capacity & Pricing
    max_attendees = fields.IntField(default=0)  # 0 means unlimited
    current_attendees = fields.IntField(default=0)
    is_free = fields.BooleanField(default=True)
    ticket_price = fields.DecimalField(precision=2, default=0.0)
    currency = fields.StringField(max_length=3, default='USD')
    
    # Images
    images = fields.EmbeddedDocumentListField(EventImage, default=list)
    cover_image = fields.StringField(default='')  # Primary cover image URL
    
    # Additional Information
    tags = fields.ListField(fields.StringField(max_length=50), default=list)
    requirements = fields.StringField(default='')  # What attendees need to bring/know
    schedule = fields.StringField(default='')  # Detailed schedule
    featured_artists = fields.ListField(fields.StringField(), default=list)  # Names of featured artists
    
    # SEO & Visibility
    is_featured = fields.BooleanField(default=False)
    views_count = fields.IntField(default=0)
    
    # Timestamps
    created_at = fields.DateTimeField(default=timezone.now)
    updated_at = fields.DateTimeField(default=timezone.now)
    published_at = fields.DateTimeField(default=None, null=True)
    
    meta = {
        'collection': 'events',
        'indexes': [
            'slug',
            'artist',
            'status',
            'category',
            'start_date',
            'is_featured',
            {'fields': ['title'], 'collation': {'locale': 'en', 'strength': 2}},  # Case-insensitive search
            {'fields': ['-created_at']},
            {'fields': ['-start_date']},
        ],
        'ordering': ['-start_date']
    }
    
    def clean(self):
        """Validate event data before saving"""
        # Ensure end_date is after start_date
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        
        # Ensure registration deadline is before start date
        if self.registration_deadline and self.start_date:
            if self.registration_deadline > self.start_date:
                raise ValueError("Registration deadline must be before event start date")
        
        # Generate slug from title if not provided
        if not self.slug and self.title:
            self.slug = self._generate_unique_slug()
        
        # Update cover_image from primary image
        if self.images:
            primary_images = [img for img in self.images if img.is_primary]
            if primary_images:
                self.cover_image = primary_images[0].url
            elif self.images:
                self.cover_image = self.images[0].url
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps and validate"""
        self.updated_at = timezone.now()
        
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        # Run validation
        self.clean()
        
        return super().save(*args, **kwargs)
    
    def _generate_unique_slug(self):
        """Generate a unique slug from title"""
        from django.utils.text import slugify
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        
        # Check if slug exists
        while Event.objects(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    @property
    def is_upcoming(self):
        """Check if event is upcoming"""
        from datetime import datetime, timezone as dt_timezone
        now = datetime.now(dt_timezone.utc)
        # Ensure start_date is timezone-aware
        start = self.start_date.replace(tzinfo=dt_timezone.utc) if self.start_date.tzinfo is None else self.start_date
        return start > now
    
    @property
    def is_ongoing(self):
        """Check if event is currently happening"""
        from datetime import datetime, timezone as dt_timezone
        now = datetime.now(dt_timezone.utc)
        # Ensure dates are timezone-aware
        start = self.start_date.replace(tzinfo=dt_timezone.utc) if self.start_date.tzinfo is None else self.start_date
        end = self.end_date.replace(tzinfo=dt_timezone.utc) if self.end_date.tzinfo is None else self.end_date
        return start <= now <= end
    
    @property
    def is_past(self):
        """Check if event has ended"""
        from datetime import datetime, timezone as dt_timezone
        now = datetime.now(dt_timezone.utc)
        # Ensure end_date is timezone-aware
        end = self.end_date.replace(tzinfo=dt_timezone.utc) if self.end_date.tzinfo is None else self.end_date
        return end < now
    
    @property
    def is_sold_out(self):
        """Check if event is sold out"""
        if self.max_attendees == 0:
            return False
        return self.current_attendees >= self.max_attendees
    
    @property
    def spots_remaining(self):
        """Get number of spots remaining"""
        if self.max_attendees == 0:
            return None  # Unlimited
        return max(0, self.max_attendees - self.current_attendees)
    
    @property
    def registration_open(self):
        """Check if registration is still open"""
        if self.is_sold_out:
            return False
        
        from datetime import datetime, timezone as dt_timezone
        now = datetime.now(dt_timezone.utc)
        
        # Check registration deadline
        if self.registration_deadline:
            deadline = self.registration_deadline.replace(tzinfo=dt_timezone.utc) if self.registration_deadline.tzinfo is None else self.registration_deadline
            if now > deadline:
                return False
        
        # Can't register for past events - inline check instead of using is_past property
        if self.end_date:
            end = self.end_date.replace(tzinfo=dt_timezone.utc) if self.end_date.tzinfo is None else self.end_date
            if end < now:
                return False
        
        return True
    
    def __str__(self):
        return f"{self.title} by {self.artist.username}"
    
    def to_dict(self):
        """Convert document to dictionary for serialization"""
        return {
            'id': str(self.id),
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'short_description': self.short_description,
            'artist': {
                'id': str(self.artist.id),
                'username': self.artist.username,
                'profile_image': self.artist.profile_image_url if hasattr(self.artist, 'profile_image_url') else None,
            },
            'category': self.category,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'registration_deadline': self.registration_deadline.isoformat() if self.registration_deadline else None,
            'location': {
                'name': self.location_name,
                'address': self.location_address,
                'city': self.location_city,
                'country': self.location_country,
                'latitude': float(self.latitude) if self.latitude else None,
                'longitude': float(self.longitude) if self.longitude else None,
            },
            'is_online': self.is_online,
            'online_link': self.online_link,
            'max_attendees': self.max_attendees,
            'current_attendees': self.current_attendees,
            'is_free': self.is_free,
            'ticket_price': float(self.ticket_price) if self.ticket_price else 0.0,
            'currency': self.currency,
            'images': [
                {
                    'url': img.url,
                    'caption': img.caption,
                    'is_primary': img.is_primary,
                } for img in self.images
            ],
            'cover_image': self.cover_image,
            'tags': self.tags,
            'requirements': self.requirements,
            'schedule': self.schedule,
            'featured_artists': self.featured_artists,
            'is_featured': self.is_featured,
            'views_count': self.views_count,
            # Commented out to avoid timezone comparison errors
            # 'is_upcoming': self.is_upcoming,
            # 'is_ongoing': self.is_ongoing,
            # 'is_past': self.is_past,
            'is_sold_out': self.is_sold_out,
            'spots_remaining': self.spots_remaining,
            'registration_open': self.registration_open,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
        }


class EventSubscription(Document):
    """
    MongoEngine Document for event subscriptions.
    Tracks which visitors are subscribed to which events.
    """
    
    STATUS_CHOICES = ('pending', 'confirmed', 'cancelled', 'attended', 'no_show')
    
    # References
    event = fields.ReferenceField(Event, required=True, reverse_delete_rule=CASCADE)
    user = fields.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    
    # Subscription Details
    status = fields.StringField(choices=STATUS_CHOICES, default='pending')
    confirmation_code = fields.StringField(unique=True, required=True, max_length=32)
    attendee_name = fields.StringField(max_length=200, default='')  # Name of person attending
    
    # Additional Information
    attendee_notes = fields.StringField(default='')  # Notes from the attendee
    special_requirements = fields.StringField(default='')  # Dietary, accessibility, etc.
    
    # Payment (if applicable)
    payment_method = fields.StringField(choices=('cash', 'online'), default='cash')  # Payment method choice
    payment_status = fields.StringField(default='unpaid')  # unpaid, paid, refunded
    payment_amount = fields.DecimalField(precision=2, default=0.0)
    payment_date = fields.DateTimeField(default=None, null=True)
    
    # Timestamps
    subscribed_at = fields.DateTimeField(default=timezone.now)
    confirmed_at = fields.DateTimeField(default=None, null=True)
    cancelled_at = fields.DateTimeField(default=None, null=True)
    
    # Communication
    reminder_sent = fields.BooleanField(default=False)
    reminder_sent_at = fields.DateTimeField(default=None, null=True)
    
    meta = {
        'collection': 'event_subscriptions',
        'indexes': [
            'event',
            'user',
            'status',
            'confirmation_code',
            {'fields': ['event', 'user'], 'unique': True},  # User can only subscribe once per event
            {'fields': ['-subscribed_at']},
        ]
    }
    
    @staticmethod
    def generate_confirmation_code():
        """Generate a unique confirmation code"""
        return secrets.token_urlsafe(24)
    
    def clean(self):
        """Validate subscription data"""
        # Generate confirmation code if not provided
        if not self.confirmation_code:
            self.confirmation_code = self.generate_confirmation_code()
        
        # Set payment amount from event
        if self.event and not self.payment_amount:
            self.payment_amount = self.event.ticket_price
    
    def save(self, *args, **kwargs):
        """Override save to validate and update event attendee count"""
        # Skip count update if this is being called from cancel() or confirm()
        skip_count_update = kwargs.pop('skip_count_update', False)
        
        self.clean()
        
        # Check if this is a new subscription by checking if id exists
        is_new = self.id is None
        
        result = super().save(*args, **kwargs)
        
        # Update event's current_attendees count if new subscription and not skipping
        if not skip_count_update and is_new and self.status in ['pending', 'confirmed']:
            self.event.current_attendees += 1
            self.event.save()
        
        return result
    
    def confirm(self):
        """Confirm the subscription"""
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save(skip_count_update=True)
    
    def cancel(self):
        """Cancel the subscription"""
        old_status = self.status
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        
        # Decrease event's attendee count if was previously confirmed/pending
        if old_status in ['pending', 'confirmed'] and self.event:
            # Reload the event to get fresh data
            self.event.reload()
            self.event.current_attendees = max(0, self.event.current_attendees - 1)
            self.event.save()
        
        # Save the subscription after updating event count, skip count update to avoid double processing
        self.save(skip_count_update=True)
    
    def __str__(self):
        return f"{self.user.username} → {self.event.title}"
    
    def to_dict(self):
        """Convert document to dictionary for serialization"""
        return {
            'id': str(self.id),
            'event': {
                'id': str(self.event.id),
                'title': self.event.title,
                'slug': self.event.slug,
                'cover_image': self.event.cover_image,
                'start_date': self.event.start_date.isoformat() if self.event.start_date else None,
                'location_name': self.event.location_name,
                'is_online': self.event.is_online,
            },
            'user': {
                'id': str(self.user.id),
                'username': self.user.username,
                'email': self.user.email,
                'profile_image': self.user.profile_image_url if hasattr(self.user, 'profile_image_url') else None,
            },
            'status': self.status,
            'confirmation_code': self.confirmation_code,
            'attendee_name': self.attendee_name,
            'attendee_notes': self.attendee_notes,
            'special_requirements': self.special_requirements,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment_amount': float(self.payment_amount) if self.payment_amount else 0.0,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
        }
