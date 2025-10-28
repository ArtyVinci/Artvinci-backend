"""
Views for Sales Management with Stripe Payment Integration
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from mongoengine.errors import DoesNotExist, ValidationError
import stripe
import logging

from .models import Order, OrderItem
from .serializers import (
    OrderSerializer,
    OrderListSerializer,
    OrderCreateSerializer
)
from artworks.models import Artwork
from accounts.models import User

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    """
    Create a Stripe Payment Intent for an order
    POST: Create payment intent with order items
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create payment intent for order"""
        try:
            # Validate input
            serializer = OrderCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'error': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            items_data = serializer.validated_data['items']
            
            # Create order
            order = Order(
                user=request.user,
                shipping_address=serializer.validated_data.get('shipping_address', ''),
                phone_number=serializer.validated_data.get('phone_number', ''),
                notes=serializer.validated_data.get('notes', ''),
            )
            
            # Add items to order
            total_amount = 0
            for item_data in items_data:
                artwork_id = item_data['artwork_id']
                quantity = item_data.get('quantity', 1)
                
                # Get artwork
                try:
                    artwork = Artwork.objects.get(id=artwork_id)
                    logger.info(f"Found artwork: {artwork.id} - {artwork.title}")
                    logger.info(f"Artwork type: {type(artwork)}")
                except DoesNotExist:
                    return Response(
                        {'error': f'Artwork {artwork_id} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Check availability
                if not artwork.available or artwork.status != 'published':
                    return Response(
                        {'error': f'Artwork "{artwork.title}" is not available'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Add item to order
                order.add_item(artwork, quantity)
                total_amount += float(artwork.price) * quantity
            
            # Save order first to get an ID
            logger.info(f"Saving order with {len(order.items)} items")
            try:
                # Save without validation first to bypass the issue
                order.save(validate=False)
                logger.info(f"Order saved successfully with ID: {order.id}")
            except Exception as save_error:
                logger.error(f"Error saving order: {str(save_error)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # Create Stripe Payment Intent
            try:
                payment_intent = stripe.PaymentIntent.create(
                    amount=int(total_amount * 100),  # Amount in cents
                    currency='usd',
                    metadata={
                        'order_id': str(order.id),
                        'user_id': str(request.user.id),
                        'username': request.user.username,
                    }
                )
                
                # Save payment intent ID to order
                order.payment_intent_id = payment_intent.id
                order.save(validate=False)
                
                return Response({
                    'clientSecret': payment_intent.client_secret,
                    'paymentIntentId': payment_intent.id,
                    'order': order.to_dict(),
                }, status=status.HTTP_201_CREATED)
                
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {str(e)}")
                return Response(
                    {'error': f'Payment error: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except ValidationError as e:
            logger.error(f"Validation error creating order: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': f'Invalid order data: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmPaymentView(APIView):
    """
    Confirm payment and complete order
    POST: Confirm payment intent
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Confirm payment and update order status"""
        try:
            payment_intent_id = request.data.get('payment_intent_id')
            
            if not payment_intent_id:
                return Response(
                    {'error': 'payment_intent_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get order
            try:
                order = Order.objects.get(payment_intent_id=payment_intent_id)
            except DoesNotExist:
                return Response(
                    {'error': 'Order not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify user owns this order
            if str(order.user.id) != str(request.user.id):
                return Response(
                    {'error': 'Unauthorized'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Retrieve payment intent from Stripe
            try:
                payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
                
                if payment_intent.status == 'succeeded':
                    # Update order status
                    order.status = 'completed'
                    order.save(validate=False)
                    
                    # Mark artworks as sold
                    for item in order.items:
                        try:
                            if item.artwork:
                                item.artwork.status = 'sold'
                                item.artwork.available = False
                                item.artwork.save()
                        except Exception as e:
                            # Artwork may have been deleted, skip it
                            logger.warning(f"Could not update artwork status: {str(e)}")
                            continue
                    
                    return Response({
                        'message': 'Payment confirmed successfully',
                        'order': order.to_dict(),
                    }, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {'error': f'Payment not completed. Status: {payment_intent.status}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            except stripe.error.StripeError as e:
                logger.error(f"Stripe error: {str(e)}")
                return Response(
                    {'error': f'Payment verification error: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Error confirming payment: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MyOrdersView(APIView):
    """
    Get user's orders
    GET: List all orders for authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user's orders"""
        try:
            orders = Order.objects(user=request.user).order_by('-created_at')
            
            # Filter by status if provided
            status_filter = request.GET.get('status')
            if status_filter:
                orders = orders.filter(status=status_filter)
            
            # Serialize
            orders_data = [order.to_dict(include_details=True) for order in orders]
            
            return Response({
                'orders': orders_data,
                'count': len(orders_data)
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrderDetailView(APIView):
    """
    Get order details
    GET: Retrieve specific order
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        """Get order details"""
        try:
            try:
                order = Order.objects.get(id=order_id)
            except DoesNotExist:
                return Response(
                    {'error': 'Order not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verify user owns this order
            if str(order.user.id) != str(request.user.id):
                return Response(
                    {'error': 'Unauthorized'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(
                order.to_dict(include_details=True),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtistSalesView(APIView):
    """
    Get sales for artist's artworks
    GET: List all orders containing artist's artworks
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get artist's sales"""
        try:
            # Get all artworks by this artist
            artist_artworks = Artwork.objects(artist=request.user)
            artwork_ids = [str(artwork.id) for artwork in artist_artworks]
            
            # Find all completed orders containing these artworks
            all_orders = Order.objects(status='completed').order_by('-created_at')
            
            artist_sales = []
            total_revenue = 0
            
            for order in all_orders:
                order_data = order.to_dict(include_details=True)
                artist_items = []
                
                for item in order_data.get('items', []):
                    if item['artwork'] and item['artwork']['id'] in artwork_ids:
                        artist_items.append(item)
                        total_revenue += item['price'] * item['quantity']
                
                if artist_items:
                    order_data['items'] = artist_items
                    artist_sales.append(order_data)
            
            return Response({
                'sales': artist_sales,
                'count': len(artist_sales),
                'total_revenue': total_revenue,
                'currency': 'USD'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error fetching artist sales: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeConfigView(APIView):
    """
    Get Stripe publishable key
    GET: Return Stripe public key for frontend
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Return Stripe publishable key"""
        return Response({
            'publishableKey': settings.STRIPE_PUBLISHABLE_KEY
        }, status=status.HTTP_200_OK)

