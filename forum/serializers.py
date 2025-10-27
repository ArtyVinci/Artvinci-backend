"""Serializers for forum documents (simple representation-only serializers)."""
from rest_framework import serializers
from .models import ForumCategory, ForumTopic, ForumReply


class ForumCategorySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
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
