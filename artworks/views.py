"""
Views for Artwork management using MongoEngine and MongoDB.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.conf import settings
from mongoengine.errors import ValidationError, NotUniqueError, DoesNotExist
from mongoengine.queryset.visitor import Q
import logging
import cloudinary
import cloudinary.uploader

from .models import Artwork, Purchase, ArtworkImage
from .serializers import (
    ArtworkListSerializer,
    ArtworkDetailSerializer,
    ArtworkCreateUpdateSerializer,
    PurchaseSerializer
)
from accounts.models import User

logger = logging.getLogger(__name__)


class ArtworkListCreateView(APIView):
    """
    GET: List all published artworks (public)
    POST: Create new artwork (artists only)
    """
    
    def get_permissions(self):
        """Public for GET, authenticated for POST"""
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get(self, request):
        """List all published artworks with filters"""
        try:
            # Get all published and available artworks
            artworks = Artwork.objects(status='published')
            
            # Filter by category
            category = request.query_params.get('category')
            if category:
                artworks = artworks.filter(category=category)
            
            # Filter by availability
            available = request.query_params.get('available')
            if available:
                artworks = artworks.filter(available=(available.lower() == 'true'))
            
            # Filter by artist
            artist_id = request.query_params.get('artist')
            if artist_id:
                try:
                    artist = User.objects.get(id=artist_id)
                    artworks = artworks.filter(artist=artist)
                except DoesNotExist:
                    pass
            
            # Search by title or tags
            search = request.query_params.get('search')
            if search:
                artworks = artworks.filter(
                    Q(title__icontains=search) |
                    Q(tags__icontains=search) |
                    Q(description__icontains=search)
                )
            
            # Price range filter
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')
            if min_price:
                artworks = artworks.filter(price__gte=float(min_price))
            if max_price:
                artworks = artworks.filter(price__lte=float(max_price))
            
            # Filter featured
            is_featured = request.query_params.get('is_featured')
            if is_featured and is_featured.lower() == 'true':
                artworks = artworks.filter(is_featured=True)
            
            # Sort options
            sort_by = request.query_params.get('sort', '-created_at')
            valid_sorts = {
                'newest': '-created_at',
                'oldest': 'created_at',
                'price_low': 'price',
                'price_high': '-price',
                'popular': '-likes_count',
                'views': '-views_count'
            }
            sort_field = valid_sorts.get(sort_by, sort_by)
            artworks = artworks.order_by(sort_field)
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 12))
            start = (page - 1) * page_size
            end = start + page_size
            
            total_count = artworks.count()
            artworks_page = artworks[start:end]
            
            # Serialize
            serializer = ArtworkListSerializer([artwork.to_dict() for artwork in artworks_page], many=True)
            
            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error listing artworks: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve artworks', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create new artwork (artists only)"""
        try:
            user = request.user
            
            # Check if user is an artist
            if user.role != 'artist':
                return Response(
                    {'error': 'Only artists can create artworks'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ArtworkCreateUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create artwork
            artwork = Artwork(
                artist=user,
                **serializer.validated_data
            )
            artwork.save()
            
            # Return created artwork
            detail_serializer = ArtworkDetailSerializer(artwork.to_dict())
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {'error': 'Validation error', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating artwork: {str(e)}")
            return Response(
                {'error': 'Failed to create artwork', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtworkDetailView(APIView):
    """
    GET: Retrieve artwork details (public)
    PUT/PATCH: Update artwork (artist owner only)
    DELETE: Delete artwork (artist owner only)
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request, slug):
        """Get artwork by slug"""
        try:
            print(f"=== Fetching artwork with slug: {slug} ===")
            artwork = Artwork.objects.get(slug=slug)
            print(f"Found artwork: {artwork.title}")
            
            # Increment view count
            try:
                artwork.increment_views()
                print("View count incremented")
            except Exception as e:
                print(f"Error incrementing views: {e}")
            
            # Convert to dict with error handling
            try:
                print("Converting to dict...")
                artwork_dict = artwork.to_dict()
                print(f"Dict created successfully with {len(artwork_dict)} keys")
            except Exception as e:
                print(f"Error converting artwork to dict: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to basic dict
                artwork_dict = {
                    'id': str(artwork.id),
                    'title': artwork.title,
                    'description': artwork.description or '',
                    'category': artwork.category,
                    'price': float(artwork.price) if artwork.price else 0.0,
                    'currency': artwork.currency,
                    'slug': artwork.slug,
                    'status': artwork.status or 'published',
                    'available': artwork.available,
                    'views_count': artwork.views_count or 0,
                    'likes_count': artwork.likes_count or 0,
                }
            
            print("Creating serializer...")
            serializer = ArtworkDetailSerializer(artwork_dict)
            print("Serializer created, returning response")
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except DoesNotExist:
            print(f"Artwork not found with slug: {slug}")
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"=== ERROR in get artwork: {str(e)} ===")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': 'Failed to retrieve artwork', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, slug):
        """Update artwork (owner only)"""
        return self._update_artwork(request, slug, partial=False)
    
    def patch(self, request, slug):
        """Partial update artwork (owner only)"""
        return self._update_artwork(request, slug, partial=True)
    
    def _update_artwork(self, request, slug, partial=False):
        """Helper method for updating artwork"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            artwork = Artwork.objects.get(slug=slug)
            
            # Check ownership
            if str(artwork.artist.id) != str(request.user.id):
                return Response(
                    {'error': 'You can only edit your own artworks'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ArtworkCreateUpdateSerializer(data=request.data, partial=partial)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Update fields
            for key, value in serializer.validated_data.items():
                setattr(artwork, key, value)
            
            artwork.save()
            
            detail_serializer = ArtworkDetailSerializer(artwork.to_dict())
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
            
        except DoesNotExist:
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating artwork: {str(e)}")
            return Response(
                {'error': 'Failed to update artwork', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, slug):
        """Delete artwork (owner only)"""
        try:
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            artwork = Artwork.objects.get(slug=slug)
            
            # Check ownership
            if str(artwork.artist.id) != str(request.user.id):
                return Response(
                    {'error': 'You can only delete your own artworks'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete artwork images from Cloudinary
            for image in artwork.images:
                try:
                    cloudinary.uploader.destroy(image.public_id)
                except Exception as e:
                    logger.warning(f"Failed to delete image from Cloudinary: {str(e)}")
            
            artwork.delete()
            
            return Response(
                {'message': 'Artwork deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except DoesNotExist:
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting artwork: {str(e)}")
            return Response(
                {'error': 'Failed to delete artwork'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtworkLikeView(APIView):
    """Toggle like/unlike for an artwork"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        """Toggle like for artwork"""
        try:
            artwork = Artwork.objects.get(slug=slug)
            user = request.user
            
            artwork.toggle_like(user)
            
            return Response({
                'message': 'Like toggled successfully',
                'likes_count': artwork.likes_count,
                'is_liked': artwork.is_liked_by_user(user)
            }, status=status.HTTP_200_OK)
            
        except DoesNotExist:
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error toggling like: {str(e)}")
            return Response(
                {'error': 'Failed to toggle like'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyArtworksView(APIView):
    """Get artworks created by the authenticated artist"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's own artworks"""
        try:
            user = request.user
            
            # Get all artworks by this artist
            artworks = Artwork.objects(artist=user).order_by('-created_at')
            
            serializer = ArtworkListSerializer([artwork.to_dict() for artwork in artworks], many=True)
            
            return Response({
                'count': artworks.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving user artworks: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve artworks'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtworkImageUploadView(APIView):
    """Upload images to Cloudinary for artworks"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        """Upload image(s) to artwork"""
        try:
            # Ensure Cloudinary is configured
            import os
            cloudinary.config(
                cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')),
                api_key=os.environ.get('CLOUDINARY_API_KEY', settings.CLOUDINARY_STORAGE.get('API_KEY')),
                api_secret=os.environ.get('CLOUDINARY_API_SECRET', settings.CLOUDINARY_STORAGE.get('API_SECRET')),
                secure=True
            )
            
            artwork = Artwork.objects.get(slug=slug)
            
            # Check ownership
            if str(artwork.artist.id) != str(request.user.id):
                return Response(
                    {'error': 'You can only upload images to your own artworks'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get image files (handle both single 'image' and multiple 'images')
            image_files = request.FILES.getlist('images') or request.FILES.getlist('image')
            if not image_files:
                # Try single file
                single_file = request.FILES.get('image') or request.FILES.get('images')
                if single_file:
                    image_files = [single_file]
                else:
                    return Response(
                        {'error': 'No image file provided'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            uploaded_images = []
            
            for image_file in image_files:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    image_file,
                    folder='artvinci/artworks',
                    resource_type='image'
                )
                
                # Create ArtworkImage
                artwork_image = ArtworkImage(
                    url=upload_result['secure_url'],
                    public_id=upload_result['public_id'],
                    caption=request.data.get('caption', ''),
                    is_primary=len(artwork.images) == 0  # First image is primary
                )
                
                artwork.images.append(artwork_image)
                uploaded_images.append({
                    'url': artwork_image.url,
                    'public_id': artwork_image.public_id,
                    'caption': artwork_image.caption,
                    'is_primary': artwork_image.is_primary,
                })
            
            artwork.save()
            
            return Response({
                'message': f'{len(uploaded_images)} image(s) uploaded successfully',
                'images': uploaded_images
            }, status=status.HTTP_201_CREATED)
            
        except DoesNotExist:
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            return Response(
                {'error': 'Failed to upload image', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchaseArtworkView(APIView):
    """Purchase an artwork"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a purchase (placeholder for payment integration)"""
        try:
            user = request.user
            artwork_id = request.data.get('artwork_id')
            
            if not artwork_id:
                return Response(
                    {'error': 'Artwork ID is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            artwork = Artwork.objects.get(id=artwork_id)
            
            # Check if artwork is available
            if not artwork.available or artwork.status != 'published':
                return Response(
                    {'error': 'This artwork is not available for purchase'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user is trying to buy their own artwork
            if str(artwork.artist.id) == str(user.id):
                return Response(
                    {'error': 'You cannot purchase your own artwork'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create purchase record
            purchase = Purchase(
                artwork=artwork,
                buyer=user,
                artist=artwork.artist,
                amount=artwork.price,
                currency=artwork.currency,
                payment_method=request.data.get('payment_method', ''),
                transaction_id=request.data.get('transaction_id', '')
            )
            purchase.save()
            
            # Mark artwork as sold (you might want to do this after payment confirmation)
            artwork.available = False
            artwork.status = 'sold'
            artwork.save()
            
            serializer = PurchaseSerializer(purchase.to_dict())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except DoesNotExist:
            return Response(
                {'error': 'Artwork not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating purchase: {str(e)}")
            return Response(
                {'error': 'Failed to process purchase', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyPurchasesView(APIView):
    """Get user's purchase history"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List user's purchases"""
        try:
            user = request.user
            purchases = Purchase.objects(buyer=user).order_by('-purchased_at')
            
            serializer = PurchaseSerializer([p.to_dict() for p in purchases], many=True)
            return Response({
                'count': purchases.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving purchases: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve purchases'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtistSalesView(APIView):
    """Get artist's sales history"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """List artist's sales"""
        try:
            user = request.user
            
            if user.role != 'artist':
                return Response(
                    {'error': 'Only artists can view sales'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            sales = Purchase.objects(artist=user).order_by('-purchased_at')
            
            serializer = PurchaseSerializer([s.to_dict() for s in sales], many=True)
            return Response({
                'count': sales.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error retrieving sales: {str(e)}")
            return Response(
                {'error': 'Failed to retrieve sales'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# AI ART ANALYSIS VIEWS
# ============================================================================

class AIArtworkAnalysisView(APIView):
    """AI-powered artwork analysis for auto-tagging and style recognition"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Analyze artwork image using AI
        
        Request body:
        {
            "image_url": "https://cloudinary.com/...",
            "artwork_id": "optional artwork ID to update"
        }
        
        Returns:
        {
            "success": true,
            "analysis": {
                "style": "Abstract",
                "colors": ["Blue", "Gold"],
                "mood": "Peaceful",
                "tags": [...],
                "description": "...",
                ...
            }
        }
        """
        try:
            print("=== AI Analysis Request ===")
            print(f"User: {request.user}")
            print(f"Data: {request.data}")
            
            from .ai_art_analyzer import get_art_analyzer
            print("✅ AI analyzer module imported")
            
            image_url = request.data.get('image_url')
            if not image_url:
                return Response(
                    {'error': 'image_url is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"📸 Image URL: {image_url[:50]}...")
            
            # Get AI analyzer - this will check for API key
            try:
                print("🔧 Initializing AI analyzer...")
                analyzer = get_art_analyzer()
                print("✅ AI analyzer initialized")
            except ValueError as ve:
                # API key not found
                print(f"❌ API Key error: {ve}")
                return Response(
                    {
                        'error': str(ve),
                        'hint': 'Add GEMINI_API_KEY to your .env file and restart Django server'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as e:
                print(f"❌ Init error: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            # Analyze the artwork
            print(f"🎨 Starting AI analysis for: {image_url[:50]}...")
            result = analyzer.analyze_artwork(image_url)
            print(f"📊 Analysis result: {result.get('success', False)}")
            
            if not result['success']:
                error_msg = result.get('error', 'Analysis failed')
                print(f"❌ Analysis failed: {error_msg}")
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            print("✅ Analysis successful!")
            
            # Optionally update artwork if artwork_id provided
            artwork_id = request.data.get('artwork_id')
            if artwork_id:
                try:
                    artwork = Artwork.objects.get(id=artwork_id, artist=request.user)
                    analysis = result['analysis']
                    
                    # Update artwork with AI suggestions
                    if analysis.get('tags'):
                        # Merge existing tags with AI tags
                        existing_tags = set(artwork.tags or [])
                        ai_tags = set(analysis['tags'][:10])  # Limit to 10 tags
                        artwork.tags = list(existing_tags | ai_tags)
                    
                    artwork.save()
                    result['artwork_updated'] = True
                    
                except DoesNotExist:
                    result['artwork_updated'] = False
                    result['update_error'] = 'Artwork not found or unauthorized'
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_detail = str(e)
            print(f"\n❌ === AI ANALYSIS ERROR ===")
            print(f"Error: {error_detail}")
            logger.error(f"Error in AI analysis: {error_detail}")
            import traceback
            traceback.print_exc()
            print("=" * 50)
            return Response(
                {
                    'error': f'AI analysis failed: {error_detail}',
                    'type': type(e).__name__
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AITagSuggestionView(APIView):
    """Generate tag suggestions based on title and description"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate tag suggestions
        
        Request body:
        {
            "title": "Artwork title",
            "description": "Artwork description (optional)"
        }
        
        Returns:
        {
            "tags": ["tag1", "tag2", ...]
        }
        """
        try:
            from .ai_art_analyzer import get_art_analyzer
            
            title = request.data.get('title')
            if not title:
                return Response(
                    {'error': 'title is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            description = request.data.get('description', '')
            
            # Get AI analyzer
            analyzer = get_art_analyzer()
            
            # Generate tags
            tags = analyzer.suggest_tags(title, description)
            
            return Response({
                'success': True,
                'tags': tags
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error generating tags: {str(e)}")
            return Response(
                {'error': f'Tag generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIDescriptionEnhancementView(APIView):
    """Enhance or generate artwork description using AI"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Enhance artwork description
        
        Request body:
        {
            "title": "Artwork title",
            "description": "Current description (optional)"
        }
        
        Returns:
        {
            "description": "Enhanced description"
        }
        """
        try:
            from .ai_art_analyzer import get_art_analyzer
            
            title = request.data.get('title')
            if not title:
                return Response(
                    {'error': 'title is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            current_description = request.data.get('description', '')
            
            # Get AI analyzer
            analyzer = get_art_analyzer()
            
            # Enhance description
            enhanced = analyzer.enhance_description(title, current_description)
            
            return Response({
                'success': True,
                'description': enhanced
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error enhancing description: {str(e)}")
            return Response(
                {'error': f'Description enhancement failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
