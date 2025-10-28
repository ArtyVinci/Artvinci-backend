from mongoengine import Document, fields
from django.utils import timezone


class Artwork(Document):
    """MongoEngine document for gallery-generated artworks."""
    prompt = fields.StringField(max_length=255, required=True)
    image_url = fields.StringField(default='')
    created_at = fields.DateTimeField(default=timezone.now)

    meta = {
        'collection': 'gallery_artworks',
        'ordering': ['-created_at']
    }

    def __str__(self):
        return f"{self.prompt} - {self.created_at:%Y-%m-%d %H:%M}"
