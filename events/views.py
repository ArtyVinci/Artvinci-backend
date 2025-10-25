"""
Views for Events management using MongoEngine and MongoDB.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from mongoengine.errors import ValidationError, NotUniqueError, DoesNotExist
from mongoengine.queryset.visitor import Q
import logging
import cloudinary.uploader

from .models import Event, EventSubscription, EventImage
from .serializers import (
    EventListSerializer,
    EventDetailSerializer,
    EventCreateUpdateSerializer,
    EventSubscriptionSerializer,
    CreateSubscriptionSerializer
)
from accounts.models import User
from .ai_service import ai_service

logger = logging.getLogger(__name__)


class EventListCreateView(APIView):
    """
    GET: List all published events (public)
    POST: Create new event (artists only)
    """
    
    def get_permissions(self):
        """Public for GET, authenticated for POST"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get(self, request):
        """List all published events with filters"""
        try:
            from datetime import datetime, timezone as dt_timezone
            
            # Get all published events
            events = Event.objects(status='published')
            
            # Filter by category
            category = request.query_params.get('category')
            if category:
                events = events.filter(category=category)
            
            # Filter by is_online
            is_online = request.query_params.get('is_online')
            if is_online:
                events = events.filter(is_online=(is_online.lower() == 'true'))
            
            # Filter by is_free
            is_free = request.query_params.get('is_free')
            if is_free:
                events = events.filter(is_free=(is_free.lower() == 'true'))
            
            # Filter by is_featured
            is_featured = request.query_params.get('is_featured')
            if is_featured:
                events = events.filter(is_featured=(is_featured.lower() == 'true'))
            
            # Filter by time (upcoming, ongoing, past)
            time_filter = request.query_params.get('time')
            now = datetime.now(dt_timezone.utc)
            
            if time_filter == 'upcoming':
                # Events that haven't started yet
                filtered_events = []
                for event in events:
                    start = event.start_date.replace(tzinfo=dt_timezone.utc) if event.start_date.tzinfo is None else event.start_date
                    if start > now:
                        filtered_events.append(event)
                events = filtered_events
            elif time_filter == 'ongoing':
                # Events currently happening
                filtered_events = []
                for event in events:
                    start = event.start_date.replace(tzinfo=dt_timezone.utc) if event.start_date.tzinfo is None else event.start_date
                    end = event.end_date.replace(tzinfo=dt_timezone.utc) if event.end_date.tzinfo is None else event.end_date
                    if start <= now <= end:
                        filtered_events.append(event)
                events = filtered_events
            elif time_filter == 'past':
                # Events that have ended
                filtered_events = []
                for event in events:
                    end = event.end_date.replace(tzinfo=dt_timezone.utc) if event.end_date.tzinfo is None else event.end_date
                    if end < now:
                        filtered_events.append(event)
                events = filtered_events
            
            # Search by title, description, or location
            search = request.query_params.get('search')
            if search and search.strip():
                search_lower = search.lower().strip()
                filtered_events = []
                for event in events:
                    if (search_lower in event.title.lower() or
                        search_lower in (event.description or '').lower() or
                        search_lower in (event.short_description or '').lower() or
                        search_lower in (event.location_name or '').lower() or
                        search_lower in (event.location_city or '').lower() or
                        search_lower in (event.location_country or '').lower() or
                        search_lower in (event.category or '').replace('_', ' ').lower()):
                        filtered_events.append(event)
                events = filtered_events
            
            # Sorting
            sort = request.query_params.get('sort', '-start_date')
            if sort == '-start_date':
                events = sorted(events, key=lambda e: e.start_date if e.start_date else datetime.min.replace(tzinfo=dt_timezone.utc), reverse=True)
            elif sort == 'start_date':
                events = sorted(events, key=lambda e: e.start_date if e.start_date else datetime.min.replace(tzinfo=dt_timezone.utc))
            elif sort == 'title':
                events = sorted(events, key=lambda e: e.title.lower())
            elif sort == '-title':
                events = sorted(events, key=lambda e: e.title.lower(), reverse=True)
            elif sort == 'ticket_price':
                events = sorted(events, key=lambda e: e.ticket_price if e.ticket_price else 0)
            elif sort == '-ticket_price':
                events = sorted(events, key=lambda e: e.ticket_price if e.ticket_price else 0, reverse=True)
            
            # Convert to list of dicts
            results = []
            for event in events:
                # Get artist info
                artist_info = None
                if event.artist:
                    artist_info = {
                        'id': str(event.artist.id),
                        'username': event.artist.username,
                        'email': event.artist.email,
                    }
                
                results.append({
                    'id': str(event.id),
                    'title': event.title,
                    'slug': event.slug,
                    'description': event.description,
                    'short_description': event.short_description or '',
                    'artist': artist_info,
                    'category': event.category,
                    'status': event.status,
                    'start_date': event.start_date.isoformat() if event.start_date else None,
                    'end_date': event.end_date.isoformat() if event.end_date else None,
                    'location_name': event.location_name or '',
                    'location_city': event.location_city or '',
                    'location_country': event.location_country or '',
                    'is_online': event.is_online,
                    'is_free': event.is_free,
                    'ticket_price': float(event.ticket_price) if event.ticket_price else 0.0,
                    'currency': event.currency or 'USD',
                    'max_attendees': event.max_attendees or 0,
                    'current_attendees': event.current_attendees or 0,
                    'cover_image': event.cover_image or '',
                    'is_featured': event.is_featured or False,
                })
            
            return Response({
                'count': len(results),
                'results': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to fetch events',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create new event (artists only)"""
        try:
            user = request.user
            
            # Check if user is an artist
            if user.role != 'artist':
                return Response({
                    'error': 'Permission denied',
                    'message': 'Only artists can create events'
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = EventCreateUpdateSerializer(data=request.data)
            
            if not serializer.is_valid():
                logger.error(f"Event validation failed: {serializer.errors}")
                logger.error(f"Request data: {request.data}")
                return Response({
                    'error': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create event instance without saving
            validated_data = serializer.validated_data
            event = Event(**validated_data)
            event.artist = user
            # Set status to published by default so it shows up immediately
            if not event.status or event.status == 'draft':
                event.status = 'published'
            event.save()
            
            logger.info(f"Event created: {event.title} by {user.username}")
            
            # Return simple response with essential data
            return Response({
                'message': 'Event created successfully',
                'slug': event.slug,
                'id': str(event.id),
                'title': event.title
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return Response({
                'error': 'Failed to create event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventDetailView(APIView):
    """
    GET: Get event details (public)
    PATCH: Update event (artist owner only)
    DELETE: Delete event (artist owner only)
    """
    
    def get_permissions(self):
        """Public for GET, authenticated for PATCH/DELETE"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get(self, request, slug):
        """Get event details by slug"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Increment views count
            event.views_count += 1
            event.save()
            
            serializer = EventDetailSerializer(event)
            
            # Check if user is subscribed (if authenticated)
            is_subscribed = False
            subscription = None
            if request.user and request.user.is_authenticated:
                subscription = EventSubscription.objects(
                    event=event,
                    user=request.user,
                    status__in=['pending', 'confirmed']  # Only active subscriptions
                ).first()
                is_subscribed = subscription is not None
            
            response_data = serializer.data
            response_data['is_subscribed'] = is_subscribed
            if subscription:
                response_data['subscription'] = EventSubscriptionSerializer(subscription).data
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching event: {str(e)}")
            return Response({
                'error': 'Failed to fetch event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, slug):
        """Update event (artist owner only)"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check ownership
            if str(event.artist.id) != str(request.user.id):
                return Response({
                    'error': 'Permission denied',
                    'message': 'You can only edit your own events'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Debug: Log coordinates being received
            logger.info(f"Updating event {slug} - Received latitude: {request.data.get('latitude')}, longitude: {request.data.get('longitude')}")
            
            serializer = EventCreateUpdateSerializer(event, data=request.data, partial=True)
            
            if not serializer.is_valid():
                logger.error(f"Event update validation failed: {serializer.errors}")
                logger.error(f"Request data: {request.data}")
                return Response({
                    'error': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            event = serializer.save()
            
            logger.info(f"Event updated: {event.title} - Saved latitude: {event.latitude}, longitude: {event.longitude}")
            
            return Response({
                'message': 'Event updated successfully',
                'event': EventDetailSerializer(event).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating event: {str(e)}")
            return Response({
                'error': 'Failed to update event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, slug):
        """Delete event (artist owner only)"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check ownership
            if str(event.artist.id) != str(request.user.id):
                return Response({
                    'error': 'Permission denied',
                    'message': 'You can only delete your own events'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Delete all images from Cloudinary
            for image in event.images:
                try:
                    cloudinary.uploader.destroy(image.public_id)
                except Exception as e:
                    logger.warning(f"Failed to delete image from Cloudinary: {str(e)}")
            
            event.delete()
            
            logger.info(f"Event deleted: {event.title}")
            
            return Response({
                'message': 'Event deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return Response({
                'error': 'Failed to delete event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventImageUploadView(APIView):
    """Upload images for an event"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        """Upload image(s) to event"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check ownership
            if str(event.artist.id) != str(request.user.id):
                return Response({
                    'error': 'Permission denied',
                    'message': 'You can only upload images to your own events'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get uploaded files
            uploaded_images = []
            
            for key in request.FILES:
                image_file = request.FILES[key]
                
                try:
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        image_file,
                        folder=f'artvinci/events/{event.slug}',
                        resource_type='image',
                        transformation=[
                            {'width': 1200, 'height': 800, 'crop': 'fill'},
                            {'quality': 'auto', 'fetch_format': 'auto'}
                        ]
                    )
                    
                    # Create EventImage
                    event_image = EventImage(
                        url=upload_result['secure_url'],
                        public_id=upload_result['public_id'],
                        caption=request.data.get(f'{key}_caption', ''),
                        is_primary=len(event.images) == 0  # First image is primary
                    )
                    
                    event.images.append(event_image)
                    uploaded_images.append({
                        'url': event_image.url,
                        'caption': event_image.caption,
                        'is_primary': event_image.is_primary
                    })
                    
                except Exception as upload_error:
                    logger.error(f"Image upload error: {str(upload_error)}")
                    continue
            
            event.save()
            
            return Response({
                'message': f'{len(uploaded_images)} image(s) uploaded successfully',
                'images': uploaded_images,
                'event': EventDetailSerializer(event).data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error uploading images: {str(e)}")
            return Response({
                'error': 'Failed to upload images',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyEventsView(APIView):
    """Get events created by the authenticated user (artist)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all events created by the authenticated user"""
        try:
            user = request.user
            
            # Get all events by this artist
            events = Event.objects(artist=user).order_by('-created_at')
            
            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                events = events.filter(status=status_filter)
            
            serializer = EventListSerializer(events, many=True)
            
            return Response({
                'count': events.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching my events: {str(e)}")
            return Response({
                'error': 'Failed to fetch your events',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventSubscribeView(APIView):
    """Subscribe to an event"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        """Subscribe to an event"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user = request.user
            
            # Check if already subscribed with an active subscription (pending or confirmed)
            active_subscription = EventSubscription.objects(
                event=event,
                user=user,
                status__in=['pending', 'confirmed']
            ).first()
            
            if active_subscription:
                return Response({
                    'error': 'Already subscribed',
                    'message': 'You are already subscribed to this event',
                    'subscription': EventSubscriptionSerializer(active_subscription).data
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if there's a cancelled subscription - if so, reactivate it instead of creating new
            cancelled_subscription = EventSubscription.objects(
                event=event,
                user=user,
                status='cancelled'
            ).first()
            
            # Check if registration is open
            if not event.registration_open:
                return Response({
                    'error': 'Registration closed',
                    'message': 'Registration for this event is no longer available'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate subscription data
            serializer = CreateSubscriptionSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'error': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # If there's a cancelled subscription, reactivate it
            if cancelled_subscription:
                cancelled_subscription.status = 'pending'
                cancelled_subscription.attendee_name = serializer.validated_data.get('attendee_name')
                cancelled_subscription.attendee_notes = serializer.validated_data.get('attendee_notes', '')
                cancelled_subscription.special_requirements = serializer.validated_data.get('special_requirements', '')
                cancelled_subscription.payment_method = serializer.validated_data.get('payment_method', 'cash')
                cancelled_subscription.payment_amount = event.ticket_price
                cancelled_subscription.cancelled_at = None
                # Generate new confirmation code for reactivated subscription
                cancelled_subscription.confirmation_code = EventSubscription.generate_confirmation_code()
                cancelled_subscription.save(skip_count_update=True)
                
                # Manually increment event attendee count
                event.current_attendees += 1
                event.save()
                
                subscription = cancelled_subscription
                logger.info(f"User {user.username} reactivated subscription to event {event.title}")
            else:
                # Create new subscription
                subscription = EventSubscription(
                    event=event,
                    user=user,
                    attendee_name=serializer.validated_data.get('attendee_name'),
                    attendee_notes=serializer.validated_data.get('attendee_notes', ''),
                    special_requirements=serializer.validated_data.get('special_requirements', ''),
                    payment_method=serializer.validated_data.get('payment_method', 'cash'),
                    payment_amount=event.ticket_price
                )
                subscription.save()
                
                logger.info(f"User {user.username} subscribed to event {event.title}")
            
            return Response({
                'message': 'Successfully subscribed to event',
                'subscription': EventSubscriptionSerializer(subscription).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error subscribing to event: {str(e)}")
            return Response({
                'error': 'Failed to subscribe to event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventUnsubscribeView(APIView):
    """Unsubscribe from an event"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, slug):
        """Unsubscribe from an event"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user = request.user
            
            # Find subscription
            subscription = EventSubscription.objects(
                event=event,
                user=user
            ).first()
            
            if not subscription:
                return Response({
                    'error': 'Not subscribed',
                    'message': 'You are not subscribed to this event'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Cancel subscription
            subscription.cancel()
            
            logger.info(f"User {user.username} unsubscribed from event {event.title}")
            
            return Response({
                'message': 'Successfully unsubscribed from event'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error unsubscribing from event: {str(e)}")
            return Response({
                'error': 'Failed to unsubscribe from event',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MySubscriptionsView(APIView):
    """Get events the authenticated user is subscribed to"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all subscriptions for the authenticated user"""
        try:
            user = request.user
            
            # Get all subscriptions
            subscriptions = EventSubscription.objects(user=user).order_by('-subscribed_at')
            
            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                subscriptions = subscriptions.filter(status=status_filter)
            
            serializer = EventSubscriptionSerializer(subscriptions, many=True)
            
            return Response({
                'count': subscriptions.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {str(e)}")
            return Response({
                'error': 'Failed to fetch your subscriptions',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventAttendeesView(APIView):
    """Get list of attendees for an event (artist owner only)"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        """Get all attendees for an event"""
        try:
            event = Event.objects(slug=slug).first()
            
            if not event:
                return Response({
                    'error': 'Event not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check ownership
            if str(event.artist.id) != str(request.user.id):
                return Response({
                    'error': 'Permission denied',
                    'message': 'You can only view attendees for your own events'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get all subscriptions for this event
            subscriptions = EventSubscription.objects(event=event).order_by('-subscribed_at')
            
            # Filter by status if provided
            status_filter = request.query_params.get('status')
            if status_filter:
                subscriptions = subscriptions.filter(status=status_filter)
            
            serializer = EventSubscriptionSerializer(subscriptions, many=True)
            
            return Response({
                'event_title': event.title,
                'total_attendees': event.current_attendees,
                'max_attendees': event.max_attendees,
                'count': subscriptions.count(),
                'attendees': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching attendees: {str(e)}")
            return Response({
                'error': 'Failed to fetch attendees',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateEventDescriptionView(APIView):
    """Generate AI-powered event description using Gemini"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate event description"""
        try:
            # Check if user is artist
            if request.user.role != 'artist':
                return Response({
                    'error': 'Only artists can generate event descriptions'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get input data
            title = request.data.get('title', '')
            category = request.data.get('category', 'exhibition')
            location = request.data.get('location', '')
            additional_info = request.data.get('additional_info', '')
            
            # Validate required fields
            if not title:
                return Response({
                    'error': 'Event title is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate description using AI
            logger.info(f"🤖 Generating AI description for event: {title}")
            description = ai_service.generate_event_description(
                title=title,
                category=category,
                location=location,
                additional_info=additional_info
            )
            
            return Response({
                'description': description,
                'generated_by': 'Gemini AI'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Error generating event description: {str(e)}")
            return Response({
                'error': 'Failed to generate description',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatbotView(APIView):
    """AI Chatbot for event discovery (visitors only)"""
    permission_classes = [AllowAny]  # Allow unauthenticated users
    
    def post(self, request):
        """Handle chatbot conversation"""
        try:
            from .chatbot_service import chatbot
            
            message = request.data.get('message', '').strip()
            user_context = request.data.get('context', {})
            
            if not message:
                return Response({
                    'error': 'Message is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if this is a greeting request
            if message.lower() == '__greeting__':
                response = chatbot.get_greeting()
            else:
                # Generate AI response
                logger.info(f"🤖 Chatbot received message: {message}")
                response = chatbot.generate_response(message, user_context)
            
            return Response(response, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Chatbot error: {str(e)}")
            return Response({
                'text': "Désolé, j'ai rencontré un problème technique. Pouvez-vous réessayer ?",
                'events': [],
                'has_events': False
            }, status=status.HTTP_200_OK)  # Return 200 with error message for better UX
