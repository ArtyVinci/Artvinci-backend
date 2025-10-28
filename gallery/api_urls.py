from django.urls import path
from .views import api_generate, api_list

app_name = 'gallery_api'

urlpatterns = [
    path('generate/', api_generate, name='generate'),
    path('', api_list, name='list'),
]
