from django.urls import path
from .views import generate_art

app_name = 'gallery'

urlpatterns = [
    path('', generate_art, name='generate_art'),
]
