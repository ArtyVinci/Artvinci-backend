"""
URL configuration for ventes (sales) app
"""

from django.urls import path
from .views import (
    CreatePaymentIntentView,
    ConfirmPaymentView,
    MyOrdersView,
    OrderDetailView,
    ArtistSalesView,
    StripeConfigView,
)

app_name = 'ventes'

urlpatterns = [
    # Stripe Configuration
    path('config/', StripeConfigView.as_view(), name='stripe-config'),
    
    # Payment
    path('create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('confirm-payment/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    
    # Orders
    path('orders/', MyOrdersView.as_view(), name='my-orders'),
    path('orders/<str:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    
    # Artist Sales
    path('sales/', ArtistSalesView.as_view(), name='artist-sales'),
]
