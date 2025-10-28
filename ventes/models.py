"""
MongoEngine models for Sales Management (Gestion des ventes) in Artvinci application.
Manages orders and transactions for artworks.
"""

from mongoengine import Document, EmbeddedDocument, fields, CASCADE
from django.utils import timezone
from decimal import Decimal


class OrderItem(EmbeddedDocument):
    """
    Embedded document representing an item in an order.
    Each order item contains one artwork purchase.
    """
    artwork = fields.ReferenceField('artworks.Artwork', required=True)
    quantity = fields.IntField(min_value=1, default=1)  # Usually 1 for unique artworks
    price = fields.DecimalField(precision=2, required=True, min_value=0)  # Price at time of purchase
    
    meta = {
        'ordering': ['artwork']
    }
    
    def __str__(self):
        return f"{self.quantity}x {self.artwork.title} @ {self.price}"


class Order(Document):
    """
    MongoEngine Order Document for managing artwork purchases.
    An order can contain multiple artworks and tracks payment status.
    """
    
    STATUS_CHOICES = ('pending', 'completed', 'cancelled', 'refunded')
    
    # Customer Information
    user = fields.ReferenceField('User', required=True, reverse_delete_rule=CASCADE)
    
    # Order Items
    items = fields.EmbeddedDocumentListField(OrderItem, default=list)
    
    # Pricing
    total_price = fields.DecimalField(precision=2, required=True, min_value=0)
    currency = fields.StringField(max_length=3, default='USD')
    
    # Status
    status = fields.StringField(choices=STATUS_CHOICES, default='pending')
    
    # Payment Information (Stripe)
    payment_intent_id = fields.StringField(default='')  # Stripe Payment Intent ID
    payment_method = fields.StringField(default='stripe')  # Payment gateway used
    
    # Shipping/Contact Information (optional)
    shipping_address = fields.StringField(default='')
    phone_number = fields.StringField(default='')
    notes = fields.StringField(default='')
    
    # Timestamps
    created_at = fields.DateTimeField(default=timezone.now)
    updated_at = fields.DateTimeField(default=timezone.now)
    completed_at = fields.DateTimeField(default=None, null=True)
    
    meta = {
        'collection': 'orders',
        'indexes': [
            'user',
            'status',
            'payment_intent_id',
            {'fields': ['-created_at']},
        ],
        'ordering': ['-created_at']
    }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamps"""
        self.updated_at = timezone.now()
        
        # Set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        return super().save(*args, **kwargs)
    
    def calculate_total(self):
        """Calculate total price from order items"""
        total = Decimal('0.00')
        for item in self.items:
            total += Decimal(str(item.price)) * item.quantity
        return total
    
    def add_item(self, artwork, quantity=1, price=None):
        """Add an artwork to the order"""
        if price is None:
            price = artwork.price
        
        order_item = OrderItem(
            artwork=artwork,
            quantity=quantity,
            price=price
        )
        self.items.append(order_item)
        self.total_price = self.calculate_total()
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.status}"
    
    def to_dict(self, include_details=True):
        """Convert order to dictionary for serialization"""
        data = {
            'id': str(self.id),
            'user': {
                'id': str(self.user.id),
                'username': self.user.username,
                'email': self.user.email,
            } if self.user else None,
            'total_price': float(self.total_price),
            'currency': self.currency,
            'status': self.status,
            'payment_intent_id': self.payment_intent_id,
            'payment_method': self.payment_method,
            'shipping_address': self.shipping_address,
            'phone_number': self.phone_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        if include_details:
            from artworks.models import Artwork
            from mongoengine.errors import DoesNotExist
            from bson import ObjectId
            import logging
            logger = logging.getLogger(__name__)
            
            items_list = []
            for item in self.items:
                artwork_data = None
                
                # Get the raw artwork reference
                artwork_ref = item._data.get('artwork')
                logger.info(f"Raw artwork reference: {artwork_ref}, type: {type(artwork_ref)}")
                
                if artwork_ref:
                    try:
                        # Convert to ObjectId if it's not already
                        if isinstance(artwork_ref, str):
                            artwork_id = ObjectId(artwork_ref)
                        elif hasattr(artwork_ref, 'id'):
                            artwork_id = artwork_ref.id
                        else:
                            artwork_id = artwork_ref
                        
                        logger.info(f"Fetching artwork with ID: {artwork_id}")
                        
                        # Fetch the artwork directly from the database
                        artwork = Artwork.objects.get(id=artwork_id)
                        
                        artwork_data = {
                            'id': str(artwork.id),
                            'title': artwork.title,
                            'primary_image': artwork.primary_image,
                            'artist': {
                                'id': str(artwork.artist.id),
                                'username': artwork.artist.username,
                            } if artwork.artist else None,
                        }
                        logger.info(f"Successfully fetched artwork: {artwork.title}")
                        
                    except DoesNotExist:
                        logger.warning(f"Artwork {artwork_id} does not exist in database")
                    except Exception as e:
                        logger.error(f"Error fetching artwork: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Use placeholder if artwork couldn't be retrieved
                if not artwork_data:
                    logger.warning("Using placeholder for missing artwork")
                    artwork_data = {
                        'id': 'deleted',
                        'title': 'Artwork no longer available',
                        'primary_image': None,
                        'artist': None,
                    }
                
                items_list.append({
                    'artwork': artwork_data,
                    'quantity': item.quantity,
                    'price': float(item.price),
                })
            
            data['items'] = items_list
        else:
            data['items_count'] = len(self.items)
        
        return data
