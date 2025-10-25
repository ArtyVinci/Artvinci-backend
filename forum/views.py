"""Basic API views for forum management (categories, topics, replies)."""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from mongoengine.errors import DoesNotExist
from django.utils import timezone
from datetime import timedelta

from .models import ForumCategory, ForumTopic, ForumReply, ForumTopicView
from .serializers import (
    ForumCategorySerializer,
    ForumTopicSerializer,
    ForumReplySerializer,
)


class CategoryListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        cats = ForumCategory.objects.order_by('name')
        return Response([c.to_dict() for c in cats], status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        name = data.get('name')
        description = data.get('description', '')
        if not name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)
        # Prevent duplicate by name
        existing = ForumCategory.objects(name__iexact=name).first()
        if existing:
            return Response({'error': 'Category already exists'}, status=status.HTTP_400_BAD_REQUEST)
        cat = ForumCategory(name=name, description=description)
        cat.save()
        return Response(cat.to_dict(), status=status.HTTP_201_CREATED)


class TopicListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        category_id = request.query_params.get('category')
        search = request.query_params.get('search')
        topics = ForumTopic.objects
        if category_id:
            topics = topics.filter(category=category_id)
        if search:
            s = search.strip().lower()
            topics = [t for t in topics if s in (t.title or '').lower() or s in (t.content or '').lower()]

        results = [t.to_dict() for t in topics]
        return Response({'count': len(results), 'results': results}, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        data = request.data
        title = data.get('title')
        content = data.get('content')
        category_id = data.get('category')

        if not title or not content or not category_id:
            return Response({'error': 'title, content and category are required'}, status=status.HTTP_400_BAD_REQUEST)

        category = ForumCategory.objects(id=category_id).first()
        if not category:
            return Response({'error': 'category not found'}, status=status.HTTP_404_NOT_FOUND)

        topic = ForumTopic(title=title, content=content, category=category, author=user)
        topic.save()
        return Response(topic.to_dict(), status=status.HTTP_201_CREATED)


class TopicDetailView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, topic_id):
        topic = ForumTopic.objects(id=topic_id).first()
        if not topic:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
        # increment view count atomically but avoid double-counting from rapid
        # repeat requests (React StrictMode or user reload). We record a short
        # recent view (per user or per IP) and only increment when no recent
        # view exists for the same viewer inside the window.
        try:
            # determine viewer identity
            viewer = request.user if getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False) else None
            # best-effort client IP
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            client_ip = (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')) or None

            # time window to ignore repeated views (seconds)
            window_seconds = 60
            cutoff = timezone.now() - timedelta(seconds=window_seconds)

            recent_view = None
            if viewer:
                recent_view = ForumTopicView.objects(topic=topic, user=viewer, created_at__gt=cutoff).first()
            if not recent_view and client_ip:
                recent_view = ForumTopicView.objects(topic=topic, ip=client_ip, created_at__gt=cutoff).first()

            if not recent_view:
                # record the view and increment atomically
                try:
                    v = ForumTopicView(topic=topic, user=viewer if viewer else None, ip=client_ip)
                    v.save()
                except Exception:
                    # non-fatal: ignore view record failures
                    pass
                try:
                    ForumTopic.objects(id=topic_id).update_one(inc__views_count=1)
                except Exception:
                    # non-fatal: ignore increment errors
                    pass

            # re-fetch topic to return fresh counts
            topic = ForumTopic.objects(id=topic_id).first()
        except Exception:
            # non-fatal: on any error just return the topic as-is
            pass

        return Response(topic.to_dict(include_replies=True), status=status.HTTP_200_OK)

    def patch(self, request, topic_id):
        topic = ForumTopic.objects(id=topic_id).first()
        if not topic:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
        # Only author can update
        if str(topic.author.id) != str(request.user.id):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        data = request.data
        title = data.get('title')
        content = data.get('content')
        if title:
            topic.title = title
        if content:
            topic.content = content
        topic.save()
        return Response(topic.to_dict(include_replies=True), status=status.HTTP_200_OK)

    def delete(self, request, topic_id):
        topic = ForumTopic.objects(id=topic_id).first()
        if not topic:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
        if str(topic.author.id) != str(request.user.id):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        topic.delete()
        return Response({'message': 'Topic deleted'}, status=status.HTTP_200_OK)


class ReplyListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, topic_id):
        replies = ForumReply.objects(topic=topic_id).order_by('created_at')
        return Response([r.to_dict() for r in replies], status=status.HTTP_200_OK)

    def post(self, request, topic_id):
        user = request.user
        topic = ForumTopic.objects(id=topic_id).first()
        if not topic:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
        content = request.data.get('content')
        if not content:
            return Response({'error': 'content is required'}, status=status.HTTP_400_BAD_REQUEST)
        reply = ForumReply(topic=topic, author=user, content=content)
        reply.save()
        # increment reply count on topic (keeps counts fast for list views if we choose to materialize)
        try:
            ForumTopic.objects(id=topic_id).update_one(inc__replies_count=1)
        except Exception:
            pass
        return Response(reply.to_dict(), status=status.HTTP_201_CREATED)


class ReplyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, reply_id):
        reply = ForumReply.objects(id=reply_id).first()
        if not reply:
            return Response({'error': 'Reply not found'}, status=status.HTTP_404_NOT_FOUND)
        if str(reply.author.id) != str(request.user.id):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        reply.delete()
        return Response({'message': 'Reply deleted'}, status=status.HTTP_200_OK)


class TopicHelpfulView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, topic_id):
        topic = ForumTopic.objects(id=topic_id).first()
        if not topic:
            return Response({'error': 'Topic not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            ForumTopic.objects(id=topic_id).update_one(inc__helpful_count=1)
            topic = ForumTopic.objects(id=topic_id).first()
        except Exception:
            pass
        return Response({'helpful_count': int(topic.helpful_count or 0)}, status=status.HTTP_200_OK)


class ReplyHelpfulView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reply_id):
        reply = ForumReply.objects(id=reply_id).first()
        if not reply:
            return Response({'error': 'Reply not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            ForumReply.objects(id=reply_id).update_one(inc__helpful_count=1)
            reply = ForumReply.objects(id=reply_id).first()
        except Exception:
            pass
        return Response({'helpful_count': int(reply.helpful_count or 0)}, status=status.HTTP_200_OK)
