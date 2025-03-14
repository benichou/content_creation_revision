# hello/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseNotAllowed
import logging

logger = logging.getLogger('waitress')

class LogRequestsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(f"Incoming request: {request.method} {request.path}")
        response = self.get_response(request)
        logger.info(f"Response status: {response.status_code} for {request.method} {request.path}")
        return response
    

        


class DisableTraceTrackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ['GET', 'POST', 'PUT', 'DELETE']:
            return HttpResponseNotAllowed(['GET', 'HEAD', 'OPTIONS'])
       
        response = self.get_response(request)
        return response
    
class SetStrictTransportAndContenetSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'; form-action 'none';"
        return response

