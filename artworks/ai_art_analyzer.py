"""
AI Art Style Recognition & Auto-Tagging Service
Uses Google Gemini Vision API to analyze artwork images
"""

import os
import google.generativeai as genai
from typing import Dict, List
import json
import requests
from io import BytesIO
from PIL import Image


class ArtworkAIAnalyzer:
    """AI-powered artwork analysis using Google Gemini"""
    
    def __init__(self):
        """Initialize Gemini AI"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # List available models first
        print("\n📋 Checking available Gemini models...")
        try:
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
                    print(f"  ✅ {m.name}")
            
            if not available_models:
                raise ValueError("No models available for generateContent")
            
            # Use the first available model that supports vision
            vision_models = [m for m in available_models if 'vision' in m.lower() or '1.5' in m]
            if vision_models:
                model_name = vision_models[0]
            else:
                model_name = available_models[0]
            
            print(f"\n🎯 Selected model: {model_name}")
            self.model = genai.GenerativeModel(model_name)
            print("✅ AI analyzer initialized successfully\n")
            
        except Exception as e:
            print(f"\n❌ Error listing models: {e}")
            # Fallback: try common model names
            print("⚠️ Trying fallback models...")
            for model_name in ['gemini-1.5-flash', 'gemini-pro', 'gemini-1.0-pro']:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    print(f"✅ Using fallback model: {model_name}\n")
                    return
                except:
                    continue
            raise ValueError("Could not initialize any Gemini model. Check your API key.")
    
    def analyze_artwork(self, image_url: str) -> Dict:
        """
        Analyze artwork image and extract:
        - Art style (Abstract, Realism, Impressionism, etc.)
        - Dominant colors
        - Mood/emotion
        - Subject matter
        - Suggested tags
        - Complexity level
        - Recommended price range (optional)
        
        Args:
            image_url: URL of the artwork image (Cloudinary URL)
            
        Returns:
            Dict with analysis results
        """
        try:
            # Download image from URL
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            
            # Prepare the prompt for Gemini
            prompt = """
            You are an expert art critic and analyst. Analyze this artwork image and provide a detailed analysis in JSON format.
            
            Return ONLY a valid JSON object with the following structure (no markdown, no code blocks, just pure JSON):
            {
                "style": "primary art style (e.g., Abstract, Realism, Impressionism, Cubism, Surrealism, Pop Art, etc.)",
                "styles": ["list of all applicable art styles"],
                "colors": ["list of 3-5 dominant colors"],
                "mood": "overall mood/emotion (e.g., Peaceful, Energetic, Melancholic, Joyful, etc.)",
                "subject": "main subject matter (e.g., Portrait, Landscape, Still Life, Abstract Forms, etc.)",
                "tags": ["10-15 relevant tags for searchability"],
                "complexity": "Low, Medium, or High",
                "description": "A compelling 2-3 sentence description of the artwork",
                "technique": "painting technique or medium used (e.g., Oil, Watercolor, Digital, Mixed Media, etc.)",
                "composition": "brief description of composition (e.g., Balanced, Dynamic, Minimalist, etc.)",
                "suggested_price_range": "price range suggestion in USD (e.g., $100-$500, $500-$1000, $1000+)"
            }
            
            Be specific and professional. Focus on art terminology and marketability.
            """
            
            # Generate analysis
            response = self.model.generate_content([prompt, img])
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Extract JSON from code block
                lines = response_text.split('\n')
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith('```'):
                        in_json = not in_json
                        continue
                    if in_json or (not line.strip().startswith('```')):
                        json_lines.append(line)
                response_text = '\n'.join(json_lines).strip()
            
            analysis = json.loads(response_text)
            
            # Add confidence score and model info
            analysis['confidence'] = 'high'
            analysis['analyzed_by'] = 'google-gemini-ai'
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Failed to download image: {str(e)}'
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'Failed to parse AI response: {str(e)}',
                'raw_response': response_text if 'response_text' in locals() else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }
    
    def suggest_tags(self, title: str, description: str = None) -> List[str]:
        """
        Generate additional tags based on title and description
        
        Args:
            title: Artwork title
            description: Artwork description (optional)
            
        Returns:
            List of suggested tags
        """
        try:
            prompt = f"""
            Based on this artwork information, suggest 10 relevant search tags.
            
            Title: {title}
            Description: {description or 'Not provided'}
            
            Return ONLY a JSON array of strings (no markdown, no explanation):
            ["tag1", "tag2", "tag3", ...]
            
            Focus on: style keywords, emotions, colors, subjects, and searchable terms.
            """
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            
            tags = json.loads(response_text)
            return tags
            
        except Exception as e:
            print(f"Failed to generate tags: {e}")
            return []
    
    def enhance_description(self, title: str, current_description: str = None) -> str:
        """
        Generate or enhance artwork description
        
        Args:
            title: Artwork title
            current_description: Existing description to enhance (optional)
            
        Returns:
            Enhanced description
        """
        try:
            if current_description:
                prompt = f"""
                Enhance this artwork description to make it more compelling and professional:
                
                Title: {title}
                Current Description: {current_description}
                
                Return an enhanced version (2-3 sentences) that is:
                - More engaging and descriptive
                - Uses art terminology
                - Highlights emotional impact
                - Makes it more marketable
                
                Return ONLY the enhanced description text, no quotes, no markdown.
                """
            else:
                prompt = f"""
                Create a compelling description for an artwork titled "{title}".
                
                Write 2-3 sentences that are:
                - Engaging and evocative
                - Professional and artistic
                - Marketable
                
                Return ONLY the description text, no quotes, no markdown.
                """
            
            response = self.model.generate_content(prompt)
            return response.text.strip().strip('"').strip("'")
            
        except Exception as e:
            print(f"Failed to enhance description: {e}")
            return current_description or ""


# Singleton instance
_analyzer_instance = None

def get_art_analyzer():
    """Get or create AI analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ArtworkAIAnalyzer()
    return _analyzer_instance
