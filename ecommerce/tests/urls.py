"""
Test URL configuration for ecommerce tests.
Includes the full ecommerce API URLs (router + JWT + etc.) under the
'ecommerce_api' namespace so that
  reverse('ecommerce_api:product-list')
  reverse('ecommerce_api:token_obtain_pair')
all work.
"""
from django.urls import path, include

# Import the full api_urls urlpatterns (router + JWT + all extra paths)
import ecommerce.api_urls

urlpatterns = [
    # Mount the full ecommerce API at /api/ecommerce/ WITH namespace
    path('api/ecommerce/', include(
        (ecommerce.api_urls.urlpatterns, 'ecommerce_api'),
        namespace='ecommerce_api',
    )),
    # Also mount WITHOUT namespace for tests that use bare reverse('product-list')
    path('api/ecommerce/v1/', include(ecommerce.api_urls.urlpatterns)),
]
