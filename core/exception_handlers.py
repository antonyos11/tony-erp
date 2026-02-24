"""
Custom Exception Handler for REST Framework
يضمن إرجاع JSON في جميع الحالات بدلاً من HTML
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    معالج استثناءات مخصص يضمن إرجاع JSON دائماً
    """
    # استدعاء المعالج الافتراضي أولاً
    response = exception_handler(exc, context)
    
    # إذا كان هناك استجابة من المعالج الافتراضي
    if response is not None:
        # تحسين رسالة الخطأ
        error_data = {
            'error': True,
            'status_code': response.status_code,
        }
        
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                error_data['message'] = str(response.data['detail'])
            else:
                error_data['details'] = response.data
        elif isinstance(response.data, list):
            error_data['messages'] = response.data
        else:
            error_data['message'] = str(response.data)
        
        response.data = error_data
        return response
    
    # معالجة استثناءات أخرى لم يتم التعامل معها
    if isinstance(exc, Http404):
        return Response({
            'error': True,
            'status_code': 404,
            'message': 'المورد المطلوب غير موجود'
        }, status=status.HTTP_404_NOT_FOUND)
    
    if isinstance(exc, PermissionDenied):
        return Response({
            'error': True,
            'status_code': 403,
            'message': 'ليس لديك صلاحية للوصول لهذا المورد'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # خطأ غير متوقع
    logger.error(f"Unhandled exception in API: {exc}", exc_info=True)
    return Response({
        'error': True,
        'status_code': 500,
        'message': 'حدث خطأ في الخادم'
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
