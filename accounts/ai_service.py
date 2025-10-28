"""
AI Service for User Management using Google Gemini
"""
import os
import google.generativeai as genai
from django.conf import settings
import logging
from accounts.models import User

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

class UserAIService:
    """Service for AI-powered user management features"""

    def __init__(self):
        # Initialize model with error handling
        try:
            self.model = genai.GenerativeModel('models/gemini-2.5-flash')
            logger.info("✅ Gemini model initialized successfully for user AI service")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

    def generate_profile_bio(self, user):
        """
        Generate an attractive profile bio using Gemini AI based on user's activity

        Args:
            user (User): User instance

        Returns:
            str: Generated bio (under 150 words)
        """
        try:
            # Gather user data for context
            user_data = self._gather_user_context(user)

            # Build the prompt
            prompt = f"""
You are a professional art platform profile writer. Create an engaging, artistic, and concise bio for this user based on their activity and preferences.

User Profile Data:
{user_data}

Requirements:
1. Write in first person as if the user is speaking
2. Highlight their artistic interests and activities
3. Make it sound authentic and passionate about art
4. Keep it under 150 words
5. Use creative, artistic language
6. Focus on what makes them unique in the art community
7. Include their favorite art styles or interests if available
8. End with an invitation for connection or collaboration
9. Do NOT include any placeholder text or brackets
10. Make it suitable for an art platform profile

Generate ONLY the bio text, no additional formatting or explanations.
"""

            # Generate content
            response = self.model.generate_content(prompt)

            if response.text:
                bio = response.text.strip()
                logger.info(f"✅ Generated bio for user: {user.username}")
                return bio
            else:
                logger.error("❌ Gemini returned empty response for bio generation")
                return self._get_fallback_bio(user)

        except Exception as e:
            logger.error(f"❌ Error generating bio with Gemini: {str(e)}")
            return self._get_fallback_bio(user)

    def analyze_user_artwork(self, user, artwork_title, artwork_description=None):
        """
        Analyze user's artwork and generate enhanced description and tags

        Args:
            user (User): User instance
            artwork_title (str): Title of the artwork
            artwork_description (str, optional): Existing description

        Returns:
            dict: {'description': str, 'tags': list, 'style': str}
        """
        try:
            user_data = self._gather_user_context(user)

            prompt = f"""
You are an expert art critic and curator. Analyze this artwork and provide enhanced information.

Artwork Details:
- Title: {artwork_title}
{f'- Description: {artwork_description}' if artwork_description else ''}

Artist Profile Context:
{user_data}

Provide analysis in the following format:
DESCRIPTION: [2-3 sentence enhanced description]
TAGS: [comma-separated list of relevant tags]
STYLE: [primary art style/category]

Requirements:
1. Make the description more professional and engaging
2. Suggest 5-8 relevant tags
3. Identify the most appropriate art style
4. Keep description under 100 words
5. Use art-specific terminology appropriately
6. Consider the artist's profile when suggesting tags and style

Format your response exactly as shown above.
"""

            response = self.model.generate_content(prompt)

            if response.text:
                # Parse the response
                lines = response.text.strip().split('\n')
                result = {
                    'description': '',
                    'tags': [],
                    'style': ''
                }

                for line in lines:
                    if line.startswith('DESCRIPTION:'):
                        result['description'] = line.replace('DESCRIPTION:', '').strip()
                    elif line.startswith('TAGS:'):
                        tags_str = line.replace('TAGS:', '').strip()
                        result['tags'] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                    elif line.startswith('STYLE:'):
                        result['style'] = line.replace('STYLE:', '').strip()

                logger.info(f"✅ Analyzed artwork: {artwork_title} for user: {user.username}")
                return result
            else:
                logger.error("❌ Gemini returned empty response for artwork analysis")
                return self._get_fallback_artwork_analysis(artwork_title)

        except Exception as e:
            logger.error(f"❌ Error analyzing artwork with Gemini: {str(e)}")
            return self._get_fallback_artwork_analysis(artwork_title)

    def generate_personalized_recommendations(self, user):
        """
        Generate personalized artwork recommendations based on user's profile

        Args:
            user (User): User instance

        Returns:
            list: List of recommendation suggestions
        """
        try:
            user_data = self._gather_user_context(user)

            prompt = f"""
You are an expert art curator. Based on this user's profile and activity, suggest 5 personalized artwork recommendations they might enjoy.

User Profile:
{user_data}

Requirements:
1. Suggest specific types of artworks or artists they might like
2. Base recommendations on their expressed interests and activity
3. Include variety in mediums and styles
4. Explain briefly why each recommendation suits them (1-2 sentences each)
5. Keep each recommendation concise but informative
6. Focus on discovery and new experiences
7. Do NOT include numbering or bullet points
8. Return exactly 5 recommendations, one per line
9. Format: "Recommendation text here"

Generate ONLY the 5 recommendations, one per line, no additional text or formatting.
"""

            response = self.model.generate_content(prompt)

            if response.text:
                # Split by newlines and clean up
                lines = response.text.strip().split('\n')
                recommendations = []

                for line in lines:
                    line = line.strip()
                    # Remove any numbering or bullet points that might be present
                    line = line.lstrip('1234567890.-•* ')
                    if line and len(line) > 10:  # Filter out very short lines
                        recommendations.append(line)

                # Ensure we have exactly 5 recommendations
                recommendations = recommendations[:5]

                # If we don't have enough, add fallbacks
                while len(recommendations) < 5:
                    recommendations.extend(self._get_fallback_recommendations()[:5-len(recommendations)])

                logger.info(f"✅ Generated {len(recommendations)} recommendations for user: {user.username}")
                return recommendations[:5]  # Ensure max 5
            else:
                logger.error("❌ Gemini returned empty response for recommendations")
                return self._get_fallback_recommendations()

        except Exception as e:
            logger.error(f"❌ Error generating recommendations with Gemini: {str(e)}")
            return self._get_fallback_recommendations()

    def _gather_user_context(self, user):
        """Gather relevant user data for AI prompts"""
        context = f"""
Username: {user.username}
Email: {user.email}
Bio: {user.bio if hasattr(user, 'bio') and user.bio else 'Not provided'}
Face Registered: {user.face_registered if hasattr(user, 'face_registered') else 'Unknown'}
"""

        # Add more context if available (artworks, events, etc.)
        # This would need to be expanded based on actual models
        if hasattr(user, 'artworks'):
            context += f"Number of Artworks: {user.artworks.count() if hasattr(user.artworks, 'count') else 'Unknown'}\n"

        if hasattr(user, 'events_attended'):
            context += f"Events Attended: {user.events_attended.count() if hasattr(user.events_attended, 'count') else 'Unknown'}\n"

        # Add preferences if available
        if hasattr(user, 'preferences'):
            context += f"Preferences: {user.preferences}\n"

        return context.strip()

    def _get_fallback_bio(self, user):
        """Fallback bio if AI generation fails"""
        return f"Art enthusiast and creative soul. Passionate about exploring the world of art and connecting with fellow artists. Welcome to my creative journey on this platform!"

    def _get_fallback_artwork_analysis(self, artwork_title):
        """Fallback artwork analysis"""
        return {
            'description': f'A captivating artwork titled "{artwork_title}" that showcases artistic expression and creativity.',
            'tags': ['artwork', 'creative', 'original'],
            'style': 'Contemporary'
        }

    def _get_fallback_recommendations(self):
        """Fallback recommendations"""
        return [
            "Explore abstract expressionism - perfect for those who enjoy emotional and spontaneous art forms.",
            "Discover minimalist sculptures - ideal for appreciating simplicity and form in art.",
            "Check out impressionist landscapes - great for nature lovers and outdoor scenes.",
            "Try digital art collections - modern and innovative approaches to traditional subjects.",
            "Look into portrait photography - fascinating studies of human expression and emotion."
        ]

# Create singleton instance
user_ai_service = UserAIService()