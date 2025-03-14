# views.py

from django.http import HttpResponse

def root_view(request):
    return HttpResponse("Application is running", status=200)

def health_check_view(request):
    return HttpResponse("Health check OK", status=200)
