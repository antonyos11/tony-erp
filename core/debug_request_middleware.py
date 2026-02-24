"""Debug middleware to log all request details"""
import logging

logger = logging.getLogger('django.request')

class DebugRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log request details
        if request.path.startswith('/accounts/login'):
            print("="*50)
            print(f"PATH: {request.path}")
            print(f"METHOD: {request.method}")
            print(f"Content-Type: {request.content_type}")
            print(f"Content-Length: {request.META.get('CONTENT_LENGTH', 'N/A')}")
            print(f"Host: {request.META.get('HTTP_HOST', 'N/A')}")
            print(f"Origin: {request.META.get('HTTP_ORIGIN', 'N/A')}")
            if request.method == 'POST':
                try:
                    print(f"POST data keys: {list(request.POST.keys())}")
                except:
                    print("Could not read POST data")
            print("="*50)
        
        response = self.get_response(request)
        return response
