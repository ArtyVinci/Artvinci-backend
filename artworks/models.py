"""
MongoEngine models for Artwork management in Artvinci application.
Artists can create and manage their artworks, visitors can view and interact with them.
"""

from mongoengine import Document, EmbeddedDocument, fields, CASCADE
from django.utils import timezone
from datetime import datetime


class ArtworkImage(EmbeddedDocument):
    """Embedded document for artwork images"""
    url = fields.StringField(required=True)
    public_id = fields.StringField(required=True)  # Cloudinary public ID
    caption = fields.StringField(max_length=200, default='')
    is_primary = fields.BooleanField(default=False)  # Main artwork image
    uploaded_at = fields.DateTimeField(default=timezone.now)
    
    meta = {
        'ordering': ['-is_primary', '-uploaded_at']
    }


class Artwork(Document):
    """
    MongoEngine Artwork Document for storing art pieces in MongoDB.
    Artists can create artworks, visitors can view and purchase them.
    """
    
    CATEGORY_CHOICES = (
        'painting',        # Peinture
        'sculpture',       # Sculpture
        'photography',     # Photographie
        'digital_art',     # Art Numérique
        'drawing',         # Dessin
        'print',           # Gravure/Impression
        'mixed_media',     # Techniques Mixtes
        'installation',    # Installation
        'ceramics',        # Céramique
        'textile',         # Textile/Tissu
        'collage',         # Collage
        'illustration',    # Illustration
        'street_art',      # Art de Rue
        'abstract',        # Art Abstrait
        'other'            # Autre
    )
    
    STATUS_CHOICES = ('draft', 'published', 'sold', 'archived')
    
    # Basic Information
    title = fields.StringField(required=True, max_length=200)
    description = fields.StringField(required=True)
    
    # Category & Classification
    category = fields.StringField(choices=CATEGORY_CHOICES, required=True)
    tags = fields.ListField(fields.StringField(max_length=50), default=list)
    
    # Pricing & Availability
    price = fields.DecimalField(precision=2, required=True, min_value=0)
    currency = fields.StringField(max_length=3, default='USD')
    available = fields.BooleanField(default=True)  # Disponible ou non
    status = fields.StringField(choices=STATUS_CHOICES, default='published')
    
    # Artist (Owner)
    artist = fields.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    
    # Images
    images = fields.EmbeddedDocumentListField(ArtworkImage, default=list)
    primary_image = fields.StringField(default='')  # Main image URL
    
    # Physical Properties (optional)
    dimensions = fields.StringField(default='')  # e.g., "50x70 cm"
    medium = fields.StringField(default='')  # Materials used
    year_created = fields.IntField(default=None, null=True)  # Year of creation
    
    # Engagement Metrics
    views_count = fields.IntField(default=0)
    likes_count = fields.IntField(default=0)
    liked_by = fields.ListField(fields.ReferenceField('User'), default=list)  # Users who liked
    
    # SEO & Visibility
    is_featured = fields.BooleanField(default=False)
    slug = fields.StringField(unique=True)
    
    # Timestamps
    created_at = fields.DateTimeField(default=timezone.now)  # Date de création
    updated_at = fields.DateTimeField(default=timezone.now)
    published_at = fields.DateTimeField(default=None, null=True)
    
    meta = {
        'collection': 'artworks',
        'indexes': [
            'slug',
            'artist',
            'category',
            'status',
            'available',
            'is_featured',
            {'fields': ['title'], 'collation': {'locale': 'en', 'strength': 2}},
            {'fields': ['-created_at']},
            {'fields': ['-likes_count']},
            {'fields': ['-views_count']},
        ],
        'ordering': ['-created_at']
    }
    
    def clean(self):
        """Validate artwork data before saving"""
        # Generate slug from title if not provided
        if not self.slug and self.title:
            self.slug = self._generate_unique_slug()
        
        # Update primary_image from images
        if self.images:
            primary_images = [img for img in self.images if img.is_primary]
            if primary_images:
                self.primary_image = primary_images[0].url
            elif self.images:
                self.primary_image = self.images[0].url
    
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
        import secrets
        
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        
        # Check if slug exists
        while Artwork.objects(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save()
    
    def toggle_like(self, user):
        """Toggle like for a user"""
        if user in self.liked_by:
            self.liked_by.remove(user)
            self.likes_count = max(0, self.likes_count - 1)
        else:
            self.liked_by.append(user)
            self.likes_count += 1
        self.save()
    
    def is_liked_by_user(self, user):
        """Check if user has liked this artwork"""
        return user in self.liked_by
    
    def __str__(self):
        return f"{self.title} by {self.artist.username}"
    
    def to_dict(self, include_artist_detail=True):
        """Convert document to dictionary for serialization"""
        try:
            data = {
                'id': str(self.id),
                'title': self.title or '',
                'description': self.description or '',
                'category': self.category or 'other',
                'tags': self.tags or [],
                'price': float(self.price) if self.price else 0.0,
                'currency': self.currency or 'USD',
                'available': self.available if hasattr(self, 'available') else True,
                'status': self.status or 'published',
                'primary_image': self.primary_image or '',
                'images': [
                    {
                        'url': img.url,
                        'public_id': getattr(img, 'public_id', ''),
                        'caption': getattr(img, 'caption', ''),
                        'is_primary': getattr(img, 'is_primary', False),
                    }
                    for img in (self.images or [])
                ],
                'dimensions': self.dimensions or '',
                'medium': self.medium or '',
                'year_created': self.year_created,
                'views_count': self.views_count or 0,
                'likes_count': self.likes_count or 0,
                'is_featured': self.is_featured if hasattr(self, 'is_featured') else False,
                'slug': self.slug or '',
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            }
            
            if include_artist_detail and self.artist:
                try:
                    data['artist'] = {
                        'id': str(self.artist.id),
                        'username': getattr(self.artist, 'username', 'Unknown'),
                        'email': getattr(self.artist, 'email', ''),
                        'profile_image': getattr(self.artist, 'profile_image', ''),
                        'bio': getattr(self.artist, 'bio', ''),
                    }
                except Exception as e:
                    print(f"Error getting artist details: {e}")
                    data['artist'] = None
            else:
                data['artist_id'] = str(self.artist.id) if self.artist else None
            
            return data
        except Exception as e:
            print(f"Error in to_dict: {e}")
            import traceback
            traceback.print_exc()
            # Return minimal data
            return {
                'id': str(self.id) if self.id else '',
                'title': 'Error loading artwork',
                'slug': self.slug if hasattr(self, 'slug') else '',
            }


class Purchase(Document):
    """
    Purchase/Transaction record when a visitor buys an artwork
    """
    
    STATUS_CHOICES = ('pending', 'completed', 'cancelled', 'refunded')
    
    # Transaction Details
    artwork = fields.ReferenceField(Artwork, required=True)
    buyer = fields.ReferenceField('User', required=True)
    artist = fields.ReferenceField('User', required=True)
    
    # Payment Information
    amount = fields.DecimalField(precision=2, required=True)
    currency = fields.StringField(max_length=3, default='USD')
    status = fields.StringField(choices=STATUS_CHOICES, default='pending')
    
    # Payment Gateway Info (placeholder for future integration)
    payment_method = fields.StringField(default='')  # e.g., 'stripe', 'paypal'
    transaction_id = fields.StringField(default='')
    
    # Timestamps
    purchased_at = fields.DateTimeField(default=timezone.now)
    completed_at = fields.DateTimeField(default=None, null=True)
    
    meta = {
        'collection': 'purchases',
        'indexes': [
            'artwork',
            'buyer',
            'artist',
            'status',
            '-purchased_at'
        ],
        'ordering': ['-purchased_at']
    }
    
    def __str__(self):
        return f"Purchase of {self.artwork.title} by {self.buyer.username}"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'artwork': self.artwork.to_dict() if self.artwork else None,
            'buyer': {
                'id': str(self.buyer.id),
                'username': self.buyer.username,
                'email': self.buyer.email,
            } if self.buyer else None,
            'artist': {
                'id': str(self.artist.id),
                'username': self.artist.username,
            } if self.artist else None,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
