"""
URL configuration for artvinci project.
"""
from django.urls import path, include

urlpatterns = [
    # API endpoints
    path('api/auth/', include('accounts.urls', namespace='accounts')),
    path('api/events/', include('events.urls', namespace='events')),
]
