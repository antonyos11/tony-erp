"""
Autosave API Views
Provides endpoints for autosaving form data
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from core.services.autosave_service import AutosaveService, ConflictDetector
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def autosave_draft(request):
    """
    Save draft data
    
    POST /api/autosave/draft/
    {
        "model": "invoice",
        "instance_id": "123" or "new",
        "data": {...}
    }
    """
    try:
        model_name = request.data.get('model')
        instance_id = request.data.get('instance_id', 'new')
        form_data = request.data.get('data', {})
        
        if not model_name:
            return Response(
                {'error': 'Model name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = AutosaveService.save_draft(
            user_id=request.user.id,
            model_name=model_name,
            instance_id=instance_id,
            data=form_data
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'تم الحفظ التلقائي بنجاح'
            })
        else:
            return Response(
                {'error': 'فشل الحفظ التلقائي'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Autosave error: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def load_draft(request):
    """
    Load draft data
    
    GET /api/autosave/draft/?model=invoice&instance_id=123
    """
    try:
        model_name = request.GET.get('model')
        instance_id = request.GET.get('instance_id', 'new')
        
        if not model_name:
            return Response(
                {'error': 'Model name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        draft_data = AutosaveService.load_draft(
            user_id=request.user.id,
            model_name=model_name,
            instance_id=instance_id
        )
        
        if draft_data:
            return Response({
                'success': True,
                'data': draft_data.get('data'),
                'saved_at': draft_data.get('saved_at')
            })
        else:
            return Response({
                'success': False,
                'message': 'لا توجد مسودة محفوظة'
            })
    
    except Exception as e:
        logger.error(f"Load draft error: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_draft(request):
    """
    Clear draft data
    
    DELETE /api/autosave/draft/?model=invoice&instance_id=123
    """
    try:
        model_name = request.GET.get('model')
        instance_id = request.GET.get('instance_id', 'new')
        
        if not model_name:
            return Response(
                {'error': 'Model name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        AutosaveService.clear_draft(
            user_id=request.user.id,
            model_name=model_name,
            instance_id=instance_id
        )
        
        return Response({
            'success': True,
            'message': 'تم حذف المسودة'
        })
    
    except Exception as e:
        logger.error(f"Clear draft error: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acquire_edit_lock(request):
    """
    Acquire edit lock
    
    POST /api/autosave/lock/
    {
        "model": "invoice",
        "instance_id": "123"
    }
    """
    try:
        model_name = request.data.get('model')
        instance_id = request.data.get('instance_id')
        
        if not model_name or not instance_id:
            return Response(
                {'error': 'Model and instance_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success, current_lock = ConflictDetector.acquire_lock(
            model_name=model_name,
            instance_id=instance_id,
            user_id=request.user.id
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'تم الحصول على قفل التحرير'
            })
        else:
            return Response({
                'success': False,
                'locked_by': current_lock,
                'message': 'السجل قيد التحرير من قبل مستخدم آخر'
            }, status=status.HTTP_409_CONFLICT)
    
    except Exception as e:
        logger.error(f"Acquire lock error: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def release_edit_lock(request):
    """
    Release edit lock
    
    DELETE /api/autosave/lock/?model=invoice&instance_id=123
    """
    try:
        model_name = request.GET.get('model')
        instance_id = request.GET.get('instance_id')
        
        if not model_name or not instance_id:
            return Response(
                {'error': 'Model and instance_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = ConflictDetector.release_lock(
            model_name=model_name,
            instance_id=instance_id,
            user_id=request.user.id
        )
        
        return Response({
            'success': success,
            'message': 'تم تحرير القفل' if success else 'لم يتم العثور على القفل'
        })
    
    except Exception as e:
        logger.error(f"Release lock error: {e}", exc_info=True)
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
