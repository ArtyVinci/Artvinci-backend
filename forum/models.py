"""MongoEngine models for a simple forum: categories, topics, replies."""
from enum import Enum
from mongoengine import Document, fields, CASCADE
from django.utils import timezone
from datetime import timedelta


class ForumCategory(Document):
    name = fields.StringField(required=True, max_length=150, unique=True)
    # category_type is a constrained string with a set of allowed values
    class CategoryType(Enum):
        GENERAL = 'general'
        ANNOUNCEMENTS = 'announcements'
        HELP = 'help'
        TUTORIALS = 'tutorials'
        SHOWCASE = 'showcase'
        EVENTS = 'events'
        OFFTOPIC = 'offtopic'
        FEEDBACK = 'feedback'
        JOBS = 'jobs'
        MODERATION = 'moderation'

    category_type = fields.StringField(
        choices=[c.value for c in CategoryType],
        default=CategoryType.GENERAL.value,
        required=True,
        max_length=50,
    )
    description = fields.StringField(default='')
    created_at = fields.DateTimeField(default=timezone.now)

    meta = {
        'collection': 'forum_categories',
        'ordering': ['name']
    }

    def __str__(self):
        return self.name

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'type': self.category_type,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ForumTopic(Document):
    title = fields.StringField(required=True, max_length=250)
    content = fields.StringField(required=True)
    category = fields.ReferenceField(ForumCategory, required=True, reverse_delete_rule=CASCADE)
    author = fields.ReferenceField('accounts.models.User', required=True, reverse_delete_rule=CASCADE)
    created_at = fields.DateTimeField(default=timezone.now)
    updated_at = fields.DateTimeField(default=timezone.now)
    views_count = fields.IntField(default=0)
    helpful_count = fields.IntField(default=0)

    meta = {
        'collection': 'forum_topics',
        'indexes': ['category', 'author', '-created_at'],
        'ordering': ['-created_at']
    }

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def to_dict(self, include_replies=False):
        data = {
            'id': str(self.id),
            'title': self.title,
            'content': self.content,
            'category': self.category.to_dict() if self.category else None,
            'author': self.author.to_dict() if self.author else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'views_count': int(self.views_count or 0),
            'helpful_count': int(self.helpful_count or 0),
        }
        if include_replies:
            replies = ForumReply.objects(topic=self).order_by('created_at')
            data['replies'] = [r.to_dict() for r in replies]
        # always include replies_count to make list endpoints lightweight but informative
        try:
            data['replies_count'] = ForumReply.objects(topic=self).count()
        except Exception:
            data['replies_count'] = 0
        return data


class ForumReply(Document):
    topic = fields.ReferenceField(ForumTopic, required=True, reverse_delete_rule=CASCADE)
    author = fields.ReferenceField('accounts.models.User', required=True, reverse_delete_rule=CASCADE)
    content = fields.StringField(required=True)
    created_at = fields.DateTimeField(default=timezone.now)
    helpful_count = fields.IntField(default=0)

    meta = {
        'collection': 'forum_replies',
        'indexes': ['topic', 'author', '-created_at'],
        'ordering': ['created_at']
    }

    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"

    def to_dict(self):
        return {
            'id': str(self.id),
            'topic_id': str(self.topic.id) if self.topic else None,
            'author': self.author.to_dict() if self.author else None,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'helpful_count': int(self.helpful_count or 0),
        }


class ForumTopicView(Document):
    """Track recent views per topic to avoid counting rapid duplicate views

    We store a view record per (topic, user) or (topic, ip) and use a short
    time window when deciding whether to increment the topic.views_count.
    """
    topic = fields.ReferenceField(ForumTopic, required=True, reverse_delete_rule=CASCADE)
    user = fields.ReferenceField('accounts.models.User', required=False, null=True)
    ip = fields.StringField(required=False, null=True)
    created_at = fields.DateTimeField(default=timezone.now)

    meta = {
        'collection': 'forum_topic_views',
        'indexes': [
            {'fields': ['topic', 'user', '-created_at']},
            {'fields': ['topic', 'ip', '-created_at']},
        ]
    }

    def __str__(self):
        who = str(self.user.id) if self.user else (self.ip or 'anon')
        return f"View {who} -> {self.topic.id} @ {self.created_at.isoformat()}"
