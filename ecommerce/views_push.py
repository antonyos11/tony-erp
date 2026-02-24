"""
Push Notifications API Views
=============================
Endpoints for managing push subscriptions
"""

import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .push_notifications import PushSubscription, PushNotificationService


@require_http_methods(['POST'])
def subscribe_push(request):
    """
    Subscribe to push notifications
    """
    try:
        data = json.loads(request.body)
        
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')
        
        if not all([endpoint, p256dh, auth]):
            return JsonResponse({
                'error': 'بيانات الاشتراك غير مكتملة'
            }, status=400)
        
        # Create or update subscription
        subscription, created = PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
                'user': request.user if request.user.is_authenticated else None,
                'session_key': request.session.session_key if not request.user.is_authenticated else None,
                'is_active': True
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'تم الاشتراك في الإشعارات بنجاح',
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'بيانات غير صالحة'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@require_http_methods(['POST'])
def unsubscribe_push(request):
    """
    Unsubscribe from push notifications
    """
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return JsonResponse({
                'error': 'يرجى تحديد الاشتراك'
            }, status=400)
        
        deleted, _ = PushSubscription.objects.filter(endpoint=endpoint).delete()
        
        return JsonResponse({
            'success': True,
            'message': 'تم إلغاء الاشتراك بنجاح' if deleted else 'الاشتراك غير موجود'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'بيانات غير صالحة'
        }, status=400)


@require_http_methods(['GET'])
def get_vapid_public_key(request):
    """
    Get VAPID public key for client-side subscription
    """
    try:
        public_key = getattr(settings, 'VAPID_PUBLIC_KEY', None)
        
        if not public_key:
            return JsonResponse({
                'info': 'Push notifications feature is not enabled',
                'message': 'الإشعارات الفورية غير مفعلة حالياً',
                'vapid_public_key': None
            }, status=200)
        
        return JsonResponse({
            'vapid_public_key': public_key
        })
    except Exception as e:
        return JsonResponse({
            'info': 'Push notifications configuration error',
            'message': 'خطأ في إعدادات الإشعارات الفورية',
            'error': str(e)
        }, status=501)


@require_http_methods(['GET'])
def get_notification_preferences(request):
    """
    Get user's notification preferences
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'يجب تسجيل الدخول'
        }, status=401)
    
    subscriptions = PushSubscription.objects.filter(
        user=request.user,
        is_active=True
    ).exists()
    
    # Get user preferences (if we have a preferences model)
    preferences = {
        'push_enabled': subscriptions,
        'order_updates': True,
        'promotions': True,
        'price_alerts': True,
        'stock_alerts': True
    }
    
    return JsonResponse(preferences)


@require_http_methods(['POST'])
def update_notification_preferences(request):
    """
    Update user's notification preferences
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'يجب تسجيل الدخول'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        
        # Here you would save preferences to a UserPreferences model
        # For now, we just acknowledge the update
        
        return JsonResponse({
            'success': True,
            'message': 'تم تحديث إعدادات الإشعارات'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'بيانات غير صالحة'
        }, status=400)


@require_http_methods(['POST'])
def test_notification(request):
    """
    Send a test notification to the user
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'يجب تسجيل الدخول'
        }, status=401)
    
    service = PushNotificationService()
    
    count = service.send_to_user(
        user=request.user,
        notification_type='promotion',
        data={
            'message': 'هذا إشعار تجريبي! 🎉 الإشعارات تعمل بشكل صحيح.',
            'action_path': ''
        }
    )
    
    if count > 0:
        return JsonResponse({
            'success': True,
            'message': f'تم إرسال إشعار تجريبي إلى {count} جهاز'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'لم يتم العثور على اشتراكات نشطة'
        })
