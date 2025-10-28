# 🎨 AI Art Style Recognition & Auto-Tagging

## Overview
Artvinci now includes AI-powered art analysis using **Google Gemini Vision API** to automatically:
- ✅ Detect art style (Abstract, Realism, Impressionism, etc.)
- ✅ Extract dominant colors
- ✅ Analyze mood and emotion
- ✅ Identify subject matter
- ✅ Generate relevant tags for searchability
- ✅ Suggest pricing range
- ✅ Create compelling descriptions

## Setup

### 1. Get Google Gemini API Key (FREE)
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key

### 2. Add API Key to .env
```bash
GEMINI_API_KEY=your-actual-api-key-here
```

### 3. Install Dependencies
```bash
# Backend
cd Artvinci-backend
pip install google-generativeai==0.8.3 Pillow requests

# Restart Django server
python manage.py runserver
```

## API Endpoints

### 1. **Analyze Artwork Image** 
`POST /api/artworks/ai/analyze/`

Analyzes an artwork image and returns comprehensive AI insights.

**Request:**
```json
{
  "image_url": "https://res.cloudinary.com/...",
  "artwork_id": "optional-artwork-id-to-auto-update"
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "style": "Abstract",
    "styles": ["Abstract", "Modern", "Expressionism"],
    "colors": ["Cobalt Blue", "Gold", "Burnt Orange"],
    "mood": "Energetic and Dynamic",
    "subject": "Abstract Forms",
    "tags": [
      "abstract art",
      "modern",
      "blue",
      "gold",
      "dynamic",
      "expressionist",
      "contemporary",
      "bold colors",
      "geometric",
      "wall art"
    ],
    "complexity": "High",
    "description": "A mesmerizing abstract composition featuring bold cobalt blues and warm golden accents...",
    "technique": "Acrylic on Canvas",
    "composition": "Dynamic and Balanced",
    "suggested_price_range": "$500-$1000",
    "confidence": "high",
    "analyzed_by": "gemini-1.5-flash"
  }
}
```

### 2. **Suggest Tags**
`POST /api/artworks/ai/suggest-tags/`

Generate relevant tags based on title and description.

**Request:**
```json
{
  "title": "Sunset Over Mountains",
  "description": "A peaceful landscape painting"
}
```

**Response:**
```json
{
  "success": true,
  "tags": [
    "landscape",
    "sunset",
    "mountains",
    "nature",
    "peaceful",
    "orange sky",
    "scenic",
    "wall art",
    "home decor",
    "calming"
  ]
}
```

### 3. **Enhance Description**
`POST /api/artworks/ai/enhance-description/`

Generate or improve artwork description.

**Request:**
```json
{
  "title": "Urban Dreams",
  "description": "A painting of a city" // optional
}
```

**Response:**
```json
{
  "success": true,
  "description": "Urban Dreams captures the vibrant energy of city life through bold brushstrokes and dynamic composition, inviting viewers to explore the intersection of modern architecture and human experience."
}
```

## Frontend Integration

### Example Usage in React

```javascript
import { artworkService } from '../services/api';
import { showToast } from '../services/toast';

// 1. Analyze artwork after image upload
const handleImageUpload = async (file) => {
  try {
    // First upload to Cloudinary
    const uploadResult = await artworkService.uploadImage(artworkSlug, formData);
    const imageUrl = uploadResult.image_url;
    
    // Then analyze with AI
    const analysis = await artworkService.analyzeArtwork({
      image_url: imageUrl,
      artwork_id: artwork.id // optional - will auto-update artwork
    });
    
    if (analysis.success) {
      // Use AI suggestions
      setTags(analysis.analysis.tags);
      setDescription(analysis.analysis.description);
      setSuggestedPrice(analysis.analysis.suggested_price_range);
      
      showToast.success('🎨 AI Analysis complete!');
    }
  } catch (error) {
    showToast.error('AI analysis failed');
  }
};

// 2. Get tag suggestions
const handleGenerateTags = async () => {
  try {
    const result = await artworkService.suggestTags({
      title: artworkTitle,
      description: artworkDescription
    });
    
    setTags(result.tags);
    showToast.success('✨ Tags generated!');
  } catch (error) {
    showToast.error('Failed to generate tags');
  }
};

// 3. Enhance description
const handleEnhanceDescription = async () => {
  try {
    const result = await artworkService.enhanceDescription({
      title: artworkTitle,
      description: currentDescription
    });
    
    setDescription(result.description);
    showToast.success('✍️ Description enhanced!');
  } catch (error) {
    showToast.error('Failed to enhance description');
  }
};
```

## Features to Add to ArtworkForm Component

### Add AI Buttons:

1. **"✨ Analyze with AI" button** - After image upload
   - Automatically fills tags, description, style
   - Shows detected colors and mood
   - Suggests price range

2. **"🏷️ Generate Tags" button** - Next to tags input
   - Creates relevant tags from title/description

3. **"✍️ Enhance Description" button** - Next to description
   - Improves existing description or creates new one

### Example UI Addition:

```jsx
// In ArtworkForm.jsx
<div className="space-y-4">
  {/* After image upload */}
  {uploadedImage && (
    <button
      type="button"
      onClick={handleAIAnalysis}
      className="w-full btn-secondary"
    >
      ✨ Analyze with AI
    </button>
  )}
  
  {/* Tags field with AI button */}
  <div className="flex gap-2">
    <Input
      label="Tags"
      value={tags}
      onChange={(e) => setTags(e.target.value)}
    />
    <button
      type="button"
      onClick={handleGenerateTags}
      className="btn-sm btn-secondary whitespace-nowrap"
    >
      🏷️ Generate
    </button>
  </div>
  
  {/* Description with AI button */}
  <div className="relative">
    <textarea
      label="Description"
      value={description}
      onChange={(e) => setDescription(e.target.value)}
    />
    <button
      type="button"
      onClick={handleEnhanceDescription}
      className="absolute top-2 right-2 btn-sm"
    >
      ✍️ Enhance
    </button>
  </div>
</div>
```

## Cost & Limits

### Google Gemini API - FREE Tier:
- ✅ **60 requests per minute**
- ✅ **1,500 requests per day**
- ✅ **FREE** (no credit card required)
- ✅ More than enough for development and small-medium platforms

### Rate Limiting:
The free tier is generous! Perfect for:
- Development and testing
- Small to medium art platforms (< 100 artworks/day)
- Demo and academic projects

## Benefits

### For Artists:
- ⏱️ **Save time** - No manual tagging
- 🎯 **Better SEO** - More relevant tags = more visibility
- 💰 **Pricing help** - AI suggests market-appropriate prices
- ✍️ **Professional descriptions** - Sell artworks better

### For Platform:
- 🔍 **Better search** - More accurate tags = better discovery
- 📈 **Increased sales** - Better presentation = more conversions
- ⚡ **Competitive edge** - Unique AI features
- 🎨 **Data insights** - Understand your art inventory

## Troubleshooting

### Error: "GEMINI_API_KEY not found"
- Make sure you added the key to `.env`
- Restart Django server after adding the key

### Error: "Failed to download image"
- Ensure Cloudinary URL is public and accessible
- Check if image URL is valid

### Error: "Failed to parse AI response"
- Gemini occasionally returns markdown formatting
- The code handles this automatically
- If persist, check API quota

### AI gives generic results:
- Use higher quality images
- Ensure good lighting and clear artwork photos
- Try with different artwork types

## Next Steps

1. ✅ Get your Gemini API key
2. ✅ Add to `.env` file
3. ✅ Restart Django server
4. ✅ Test with `/api/artworks/ai/analyze/` endpoint
5. 🎨 Add AI buttons to ArtworkForm component
6. 🚀 Launch and watch artists love it!

## Questions?
Check Google Gemini docs: https://ai.google.dev/docs
