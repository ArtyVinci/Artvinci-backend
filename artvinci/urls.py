"""
URL configuration for artvinci project.
"""
from django.urls import path, include
from . import views

urlpatterns = [
    # Health check for Render
    path('api/health/', views.health_check, name='health_check'),

    # API endpoints
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    path('api/artworks/', include('artworks.urls', namespace='artworks')),
    path('api/events/', include('events.urls', namespace='events')),
    path('api/forum/', include('forum.urls', namespace='forum')),
    path('api/ventes/', include('ventes.urls', namespace='ventes')),
    # Gallery (AI image generator)
    path('gallery/', include('gallery.urls', namespace='gallery')),
    # Gallery API for frontend integration
    path('api/gallery/', include('gallery.api_urls', namespace='gallery_api')),
]
