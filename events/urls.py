"""
URL configuration for events app.
"""

from django.urls import path
from .views import (
    EventListCreateView,
    EventDetailView,
    EventImageUploadView,
    MyEventsView,
    EventSubscribeView,
    EventUnsubscribeView,
    MySubscriptionsView,
    EventAttendeesView,
)

app_name = 'events'

urlpatterns = [
    # Event CRUD
    path('', EventListCreateView.as_view(), name='event-list-create'),
    path('my-events/', MyEventsView.as_view(), name='my-events'),
    path('<slug:slug>/', EventDetailView.as_view(), name='event-detail'),
    path('<slug:slug>/upload-images/', EventImageUploadView.as_view(), name='event-upload-images'),
    
    # Event Subscriptions
    path('<slug:slug>/subscribe/', EventSubscribeView.as_view(), name='event-subscribe'),
    path('<slug:slug>/unsubscribe/', EventUnsubscribeView.as_view(), name='event-unsubscribe'),
    path('subscriptions/my-subscriptions/', MySubscriptionsView.as_view(), name='my-subscriptions'),
    
    # Event Management (Artist)
    path('<slug:slug>/attendees/', EventAttendeesView.as_view(), name='event-attendees'),
]
