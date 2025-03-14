# Import necessary modules from Django
from django.contrib import admin
from django.urls import path, include 
from .views import root_view, health_check_view




# Define the URL patterns for the application
urlpatterns = [
    # Map pings to the root view 
    path('', root_view, name='root_view'),
    path('healthcheck/', health_check_view, name='health_check_view'),
    # Include all the URL patterns defined in 'doc_compare.urls' and prefix them with 'doc_compare/'
    path('api/', include('api.urls')),

]
