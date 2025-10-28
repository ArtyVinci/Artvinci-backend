"""
URL configuration for artworks app
"""

from django.urls import path
from .views import (
    ArtworkListCreateView,
    ArtworkDetailView,
    ArtworkLikeView,
    MyArtworksView,
    ArtworkImageUploadView,
    PurchaseArtworkView,
    MyPurchasesView,
    ArtistSalesView,
    # AI Views
    AIArtworkAnalysisView,
    AITagSuggestionView,
    AIDescriptionEnhancementView,
)

app_name = 'artworks'

urlpatterns = [
    # Artwork CRUD
    path('', ArtworkListCreateView.as_view(), name='artwork-list-create'),
    path('my/', MyArtworksView.as_view(), name='my-artworks'),
    path('<slug:slug>/', ArtworkDetailView.as_view(), name='artwork-detail'),
    path('<slug:slug>/like/', ArtworkLikeView.as_view(), name='artwork-like'),
    path('<slug:slug>/upload-image/', ArtworkImageUploadView.as_view(), name='artwork-upload-image'),
    
    # Purchases
    path('purchase/', PurchaseArtworkView.as_view(), name='purchase-artwork'),
    path('purchases/my/', MyPurchasesView.as_view(), name='my-purchases'),
    path('sales/my/', ArtistSalesView.as_view(), name='my-sales'),
    
    # AI Features
    path('ai/analyze/', AIArtworkAnalysisView.as_view(), name='ai-analyze'),
    path('ai/suggest-tags/', AITagSuggestionView.as_view(), name='ai-suggest-tags'),
    path('ai/enhance-description/', AIDescriptionEnhancementView.as_view(), name='ai-enhance-description'),
]
