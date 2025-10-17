"""
AI Service for Event Description Generation using Google Gemini
"""
import os
import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class EventAIService:
    """Service for AI-powered event features"""
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_event_description(self, title, category, location=None, additional_info=None):
        """
        Generate an attractive event description using Gemini AI
        
        Args:
            title (str): Event title
            category (str): Event category (exhibition, workshop, etc.)
            location (str, optional): Event location
            additional_info (str, optional): Any additional context
            
        Returns:
            str: Generated description (under 100 words)
        """
        try:
            # Build the prompt
            prompt = f"""
You are a professional event promoter and copywriter for an art platform. 
Generate an attractive, engaging, and concise event description for the following event.

Event Details:
- Title: {title}
- Category: {category}
- Location: {location if location else 'Not specified'}
{f'- Additional Info: {additional_info}' if additional_info else ''}

Requirements:
1. Make it sound professional yet inviting
2. Highlight what makes this event special
3. Use enthusiastic but natural language
4. Keep it under 100 words
5. Do NOT include any placeholder text or brackets
6. Focus on what attendees will experience
7. Use action-oriented language that encourages participation
8. Do NOT mention pricing or specific dates (those are handled separately)

Generate ONLY the description text, no additional formatting or explanations.
"""
            
            # Generate content
            response = self.model.generate_content(prompt)
            
            if response.text:
                description = response.text.strip()
                logger.info(f"✅ Generated description for event: {title}")
                return description
            else:
                logger.error("❌ Gemini returned empty response")
                return self._get_fallback_description(title, category)
                
        except Exception as e:
            logger.error(f"❌ Error generating description with Gemini: {str(e)}")
            return self._get_fallback_description(title, category)
    
    def _get_fallback_description(self, title, category):
        """Fallback description if AI generation fails"""
        category_descriptions = {
            'exhibition': f'Join us for {title}, a captivating exhibition showcasing exceptional artworks. Experience creativity at its finest and immerse yourself in a world of artistic expression.',
            'workshop': f'Participate in {title}, an engaging workshop designed to enhance your artistic skills. Learn from experienced professionals and expand your creative horizons.',
            'gallery_opening': f'Celebrate the grand opening of {title}. Discover stunning artworks, meet talented artists, and be part of this exciting new chapter in the art community.',
            'art_fair': f'Explore {title}, where art lovers and collectors converge. Browse diverse collections, discover emerging talents, and find your next favorite piece.',
            'auction': f'Bid on extraordinary pieces at {title}. This exclusive auction features carefully curated artworks from renowned and emerging artists.',
            'performance': f'Experience {title}, a mesmerizing artistic performance that pushes creative boundaries. Witness art come alive in this unforgettable event.',
            'artist_talk': f'Gain insights at {title}, an intimate conversation with accomplished artists. Learn about their creative process, inspiration, and artistic journey.',
            'networking': f'Connect at {title}, where artists, collectors, and enthusiasts come together. Build meaningful relationships and expand your network in the art community.',
            'competition': f'Showcase your talent in {title}. Compete with fellow artists, receive recognition, and potentially win exciting prizes.',
            'other': f'Join us for {title}, a unique event celebrating art and creativity. Don\'t miss this special opportunity to engage with the artistic community.'
        }
        
        return category_descriptions.get(category, category_descriptions['other'])

# Create singleton instance
ai_service = EventAIService()
