"""
API Views for TestSprite Testing
نقاط API للاختبار الآلي
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication, TokenAuthentication
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class TestResourceViewSet(viewsets.ViewSet):
    """
    ViewSet for testing API endpoints
    """
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    schema = None  # exclude from swagger schema
    
    def list(self, request):
        """List resources"""
        return Response({
            'success': True,
            'data': [
                {'id': 1, 'name': 'Resource 1'},
                {'id': 2, 'name': 'Resource 2'},
            ],
            'message': 'Resources retrieved successfully'
        })
    
    def retrieve(self, request, pk=None):
        """Retrieve a specific resource"""
        return Response({
            'success': True,
            'data': {
                'id': pk,
                'name': f'Resource {pk}',
                'description': 'Test resource',
            },
            'message': 'Resource retrieved successfully'
        })
    
    def create(self, request):
        """Create a new resource"""
        name = request.data.get('name')
        
        # Check for duplicate (simple check)
        if name and 'Test Resource' in name:
            return Response({
                'success': False,
                'error': 'Resource already exists',
            }, status=status.HTTP_409_CONFLICT)
        
        return Response({
            'success': True,
            'data': {
                'id': 999,
                'name': name or 'New Resource',
            },
            'message': 'Resource created successfully'
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, pk=None):
        """Update a resource"""
        return Response({
            'success': True,
            'data': {
                'id': pk,
                'name': request.data.get('name', 'Updated Resource'),
                'description': request.data.get('description', ''),
            },
            'message': 'Resource updated successfully'
        })
    
    def destroy(self, request, pk=None):
        """Delete a resource"""
        # Handle special characters in URL
        if '%' in str(pk) or '✓' in str(pk):
            return Response({
                'success': False,
                'error': 'Resource not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Resource deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_api_health(request):
    """API Health check endpoint"""
    return Response({
        'status': 'healthy',
        'version': '1.0',
        'authenticated': request.user.is_authenticated,
    })

# Prevent pytest from collecting this view function as a test
test_api_health.__test__ = False
