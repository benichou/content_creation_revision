# Import necessary modules
from django.urls import path
#################################### Content VOICE APIs ###############################################################
from .views import DVoiceRevisionAPIView, DVoiceCreationAPIView # Content VOICE REVISION

urlpatterns = [
    path('dvoice/revision/',    DVoiceRevisionAPIView.as_view(),        name='revision'), ## dvoice api view for revision tasks
    path('dvoice/creation/',    DVoiceCreationAPIView.as_view(),        name='creation'), ## dvoice api view for creation tasks
]