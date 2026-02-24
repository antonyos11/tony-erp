"""
Mobile Authentication API
API المصادقة للتطبيقات المحمولة

يستخدم JWT tokens للمصادقة
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from typing import Dict


class MobileAuthViewSet(viewsets.ViewSet):
    """مجموعة عرض المصادقة للموبايل"""
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def login(self, request) -> Response:
        """
        تسجيل الدخول
        
        POST /api/mobile/auth/login/
        {
            "username": "user",
            "password": "password"
        }
        """
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': 'يجب إدخال اسم المستخدم وكلمة المرور'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({
                'success': False,
                'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': 'الحساب غير نشط'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # إنشاء JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # جمع بيانات المستخدم
        user_data = self._get_user_data(user)
        
        return Response({
            'success': True,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            },
            'user': user_data
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request) -> Response:
        """
        تسجيل الخروج
        
        POST /api/mobile/auth/logout/
        {
            "refresh_token": "..."
        }
        """
        try:
            refresh_token = request.data.get('refresh_token')
            
            if not refresh_token:
                return Response({
                    'success': False,
                    'error': 'لم يتم تقديم refresh_token'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'تم تسجيل الخروج بنجاح'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Token غير صالح: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def refresh(self, request) -> Response:
        """
        تحديث access token
        
        POST /api/mobile/auth/refresh/
        {
            "refresh": "..."
        }
        """
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'success': False,
                    'error': 'Refresh token مطلوب'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            refresh = RefreshToken(refresh_token)
            
            return Response({
                'success': True,
                'access': str(refresh.access_token)
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Refresh token غير صالح'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request) -> Response:
        """
        الحصول على ملف المستخدم
        
        GET /api/mobile/auth/profile/
        """
        user_data = self._get_user_data(request.user)
        
        return Response({
            'success': True,
            'user': user_data
        })
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def update_profile(self, request) -> Response:
        """
        تحديث ملف المستخدم
        
        PUT /api/mobile/auth/update_profile/
        {
            "first_name": "...",
            "last_name": "...",
            "email": "..."
        }
        """
        user = request.user
        
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.email = request.data.get('email', user.email)
        user.save()
        
        return Response({
            'success': True,
            'message': 'تم تحديث الملف الشخصي',
            'user': self._get_user_data(user)
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request) -> Response:
        """
        تغيير كلمة المرور
        
        POST /api/mobile/auth/change_password/
        {
            "old_password": "...",
            "new_password": "..."
        }
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not user.check_password(old_password):
            return Response({
                'success': False,
                'error': 'كلمة المرور القديمة غير صحيحة'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({
            'success': True,
            'message': 'تم تغيير كلمة المرور بنجاح'
        })
    
    def _get_user_data(self, user) -> Dict:
        """الحصول على بيانات المستخدم"""
        from hr.models import Employee
        
        # محاولة الحصول على بيانات الموظف
        employee_data = None
        try:
            employee = Employee.objects.get(user=user)
            employee_data = {
                'employee_id': employee.employee_id,
                'arabic_name': employee.arabic_name,
                'department': employee.department.name if employee.department else None,
                'position': employee.position.title if employee.position else None,
                'photo': employee.photo.url if employee.photo else None
            }
        except Employee.DoesNotExist:
            pass
        
        # الصلاحيات
        permissions = list(user.user_permissions.values_list('codename', flat=True))
        groups = list(user.groups.values_list('name', flat=True))
        
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'employee': employee_data,
            'permissions': permissions,
            'groups': groups
        }
