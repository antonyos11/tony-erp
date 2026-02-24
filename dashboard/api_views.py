"""
API Views للوحة المعلومات
Dashboard API Views
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone

from .cache_optimizer import DashboardDataOptimizer, get_cached_dashboard_data, clear_user_cache
from .enhanced_kpis import EnhancedKPICalculator


class DashboardDataAPIView(APIView):
    """API للحصول على بيانات لوحة المعلومات"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على جميع بيانات الداشبورد"""
        try:
            data = get_cached_dashboard_data(request.user)
            return Response({
                'success': True,
                'data': data,
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KPIAPIView(APIView):
    """API لمؤشرات الأداء الرئيسية"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """الحصول على جميع مؤشرات الأداء"""
        try:
            branch_id = request.query_params.get('branch', None)
            start_date = request.query_params.get('start_date', None)
            end_date = request.query_params.get('end_date', None)
            
            date_range = None
            if start_date and end_date:
                from datetime import datetime
                date_range = {
                    'start': datetime.strptime(start_date, '%Y-%m-%d').date(),
                    'end': datetime.strptime(end_date, '%Y-%m-%d').date()
                }
            
            calculator = EnhancedKPICalculator(
                user=request.user,
                branch=branch_id,
                date_range=date_range
            )
            
            kpis = calculator.get_all_kpis()
            
            # Return KPI categories at top level AND nested under 'data' for compatibility
            response_data = {
                'success': True,
                'data': kpis,
                'timestamp': timezone.now().isoformat()
            }
            response_data.update(kpis)
            return Response(response_data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class KPIComparisonAPIView(APIView):
    """API لمقارنة مؤشرات الأداء"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """مقارنة KPIs مع الفترة السابقة"""
        try:
            calculator = EnhancedKPICalculator(user=request.user)
            comparison = calculator.get_comparison_data()
            
            return Response({
                'success': True,
                'data': comparison,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SalesChartAPIView(APIView):
    """API لرسم المبيعات"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """بيانات رسم المبيعات"""
        try:
            days = int(request.query_params.get('days', 30))
            data = DashboardDataOptimizer.get_sales_chart_data(request.user, days=days)
            
            return Response({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InventoryChartAPIView(APIView):
    """API لرسم المخزون"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """بيانات رسم المخزون"""
        try:
            data = DashboardDataOptimizer.get_inventory_chart_data(request.user)
            
            return Response({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClearCacheAPIView(APIView):
    """API لمسح الكاش"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """مسح كاش المستخدم"""
        try:
            clear_user_cache(request.user)
            
            return Response({
                'success': True,
                'message': 'تم مسح الكاش بنجاح'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
