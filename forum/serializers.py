"""Serializers for forum documents (simple representation-only serializers)."""
from rest_framework import serializers
from .models import ForumCategory, ForumTopic, ForumReply
from .models import ForumCategory as _ForumCategory


class ForumCategorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    # expose the category type (enum-backed string)
    type = serializers.CharField(source='category_type', required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if isinstance(instance, ForumCategory):
            return instance.to_dict()
        return super().to_representation(instance)


class ForumReplySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    topic_id = serializers.CharField(read_only=True)
    author = serializers.DictField(read_only=True)
    content = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        if isinstance(instance, ForumReply):
            return instance.to_dict()
        return super().to_representation(instance)


class ForumTopicSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField()
    content = serializers.CharField()
    category = serializers.DictField(read_only=True)
    author = serializers.DictField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    replies = ForumReplySerializer(many=True, read_only=True)

    def to_representation(self, instance):
        if isinstance(instance, ForumTopic):
            # include replies by default in detailed representation
            return instance.to_dict(include_replies=True)
        return super().to_representation(instance)


class SuggestReplySerializer(serializers.Serializer):
    tone = serializers.ChoiceField(choices=[('friendly', 'friendly'), ('formal', 'formal'), ('concise', 'concise')], default='friendly', required=False)
    max_length = serializers.IntegerField(default=400, required=False)
