"""
AI Chatbot Service for Event Discovery using Google Gemini
"""
import os
import google.generativeai as genai
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import logging
import json

from .models import Event

logger = logging.getLogger(__name__)

# Configure Gemini with correct API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)


class EventChatbot:
    """Intelligent chatbot for event discovery and assistance"""
    
    def __init__(self):
        # Initialize Gemini model with error handling
        try:
            self.model = genai.GenerativeModel('models/gemini-2.5-flash')
            logger.info("✅ Gemini chatbot model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None
        self.conversation_history = []
    
    def get_relevant_events(self, interests=None, location=None, limit=5):
        """
        Query events based on user interests or location
        
        Args:
            interests (list): List of interest keywords (e.g., ['art', 'music'])
            location (str): City or location name
            limit (int): Maximum number of events to return
            
        Returns:
            list: List of relevant events
        """
        try:
            from mongoengine.queryset.visitor import Q
            
            # Build query
            query = Event.objects(
                status='published',
                start_date__gte=timezone.now()
            )
            
            # Filter by interests (category or tags)
            if interests:
                interest_query = Q()
                for interest in interests:
                    interest_lower = interest.lower()
                    interest_query |= Q(category__icontains=interest_lower)
                    interest_query |= Q(tags__icontains=interest_lower)
                    interest_query |= Q(title__icontains=interest_lower)
                    interest_query |= Q(description__icontains=interest_lower)
                
                query = query.filter(interest_query)
            
            # Filter by location
            if location:
                location_query = (
                    Q(location__city__icontains=location) |
                    Q(location__country__icontains=location) |
                    Q(location__name__icontains=location)
                )
                query = query.filter(location_query)
            
            # Get events and sort by date
            events = query.order_by('start_date')[:limit]
            
            return [self._format_event_info(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error querying events: {str(e)}")
            return []
    
    def _format_event_info(self, event):
        """Format event information for chatbot response"""
        return {
            'id': str(event.id),
            'slug': event.slug,
            'title': event.title,
            'category': event.category,
            'short_description': event.short_description or event.description[:150] + '...',
            'start_date': event.start_date.strftime('%d/%m/%Y à %H:%M') if event.start_date else 'Date à confirmer',
            'location': f"{event.location.city}, {event.location.country}" if event.location and event.location.city else 'En ligne',
            'is_free': event.is_free,
            'ticket_price': float(event.ticket_price) if event.ticket_price else 0,
            'spots_left': event.spots_left,
            'url': f"/events/{event.slug}"
        }
    
    def extract_interests_from_message(self, message):
        """Extract interest keywords from user message using AI"""
        try:
            # Simple keyword matching first (faster)
            keywords = []
            message_lower = message.lower()
            
            categories = ['exhibition', 'workshop', 'gallery', 'art', 'auction', 'performance', 
                         'artist', 'networking', 'competition', 'music', 'sport', 'culture', 
                         'cuisine', 'technology', 'fashion', 'photography', 'dance', 'theatre',
                         'expo', 'concert', 'spectacle', 'atelier']
            
            for category in categories:
                if category in message_lower:
                    keywords.append(category)
            
            if keywords:
                logger.info(f"✅ Extracted interests (simple): {keywords}")
                return keywords
            
            # If no keywords found, use AI
            prompt = f"""
Extract interest keywords from this user message. Focus on event categories, hobbies, or themes.
Return ONLY a JSON array of lowercase keywords, nothing else. No explanation.

Categories: exhibition, workshop, gallery_opening, art_fair, auction, performance, artist_talk, networking, competition, music, sport, art, culture, cuisine, technology, fashion, photography, dance, theatre

User message: "{message}"

Return format: ["keyword1", "keyword2"]
If no clear interests found, return: []
"""
            
            response = self.model.generate_content(prompt)
            if response.text:
                # Parse JSON response
                text = response.text.strip()
                # Remove markdown code blocks if present
                if '```' in text:
                    text = text.split('```')[1].strip()
                    if text.startswith('json'):
                        text = text[4:].strip()
                
                keywords = json.loads(text)
                logger.info(f"✅ Extracted interests (AI): {keywords}")
                return keywords if isinstance(keywords, list) else []
            
            return []
            
        except Exception as e:
            logger.error(f"Error extracting interests: {str(e)}")
            return []
    
    def generate_response(self, user_message, user_context=None):
        """
        Generate intelligent chatbot response using Gemini
        
        Args:
            user_message (str): User's message
            user_context (dict): Additional context (location, previous messages, etc.)
            
        Returns:
            dict: Response with text and event suggestions
        """
        try:
            # Check if model is initialized
            if not self.model:
                return {
                    'text': "Désolé, le service AI n'est pas disponible pour le moment. Cependant, je peux vous montrer nos événements disponibles !",
                    'events': self.get_relevant_events(limit=3),
                    'has_events': True
                }
            # Check if user is asking about event discovery
            discovery_keywords = ['événement', 'event', 'découvrir', 'trouver', 'cherche', 'intéresse', 'oui', 'yes', 'ok', 'proche', 'près', 'chez moi']
            is_discovery_request = any(keyword in user_message.lower() for keyword in discovery_keywords)
            
            # Extract interests from message
            interests = self.extract_interests_from_message(user_message)
            
            # Get location from context or message
            location = user_context.get('location') if user_context else None
            
            # Query relevant events
            events = []
            if is_discovery_request or interests:
                events = self.get_relevant_events(interests=interests, location=location, limit=5)
            
            # Build context for AI
            events_context = ""
            if events:
                events_context = "\n\nÉvénements disponibles:\n"
                for idx, event in enumerate(events, 1):
                    events_context += f"{idx}. {event['title']} - {event['category']} - {event['start_date']} à {event['location']}\n"
            
            # Generate AI response
            prompt = f"""
Tu es un assistant virtuel amical et enthousiaste pour une plateforme d'événements artistiques appelée ArtVinci.
Tu aides les visiteurs à découvrir des événements qui correspondent à leurs intérêts.

Règles importantes:
1. Sois chaleureux, amical et conversationnel
2. Réponds en français
3. Garde tes réponses courtes (maximum 3-4 lignes)
4. Si des événements sont disponibles, présente-les de manière enthousiaste
5. Si l'utilisateur pose une question sur les prix, types ou horaires, réponds avec les informations disponibles
6. Encourage l'utilisateur à explorer les événements
7. Ne mentionne JAMAIS que tu es une IA ou un modèle de langage

Message de l'utilisateur: "{user_message}"
{events_context}

Réponds de manière naturelle et engageante:
"""
            
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip() if response and response.text else None
            except Exception as ai_error:
                logger.error(f"AI generation failed: {str(ai_error)}")
                # Fallback to simple response
                if events:
                    response_text = f"J'ai trouvé {len(events)} événement(s) qui pourrait vous intéresser ! Découvrez-les ci-dessous."
                else:
                    response_text = "Je suis là pour vous aider à découvrir des événements ! Dites-moi ce qui vous intéresse."
            
            return {
                'text': response_text or "Désolé, je n'ai pas pu traiter votre message. Pouvez-vous reformuler ?",
                'events': events[:3] if events else [],  # Return max 3 events
                'has_events': len(events) > 0
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating chatbot response: {str(e)}")
            # Return events anyway if we have them
            events = self.get_relevant_events(limit=3)
            return {
                'text': f"Voici quelques événements disponibles qui pourraient vous intéresser ! Explorez-les ci-dessous.",
                'events': [],
                'has_events': False
            }
    
    def get_greeting(self):
        """Get initial greeting message"""
        greetings = [
            "Bonjour 👋 ! Comment ça va aujourd'hui ?",
            "Salut 👋 ! Ravi de vous voir !",
            "Bienvenue sur ArtVinci ! 👋 Comment puis-je vous aider ?",
            "Hello 👋 ! Prêt à découvrir des événements incroyables ?"
        ]
        
        import random
        greeting = random.choice(greetings)
        
        return {
            'text': f"{greeting}\n\nSouhaitez-vous découvrir un événement proche de chez vous ? 🎨",
            'events': [],
            'has_events': False
        }


# Create singleton instance
chatbot = EventChatbot()
