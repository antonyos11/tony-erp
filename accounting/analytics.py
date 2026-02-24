"""
Advanced Reporting and Analytics for Journal Entries
Modern dashboard with charts, insights, and comprehensive reports
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


@login_required
def accounting_analytics_dashboard(request):
    """
    Main analytics dashboard for accounting
    """
    try:
        # Get date range from request or default to last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        
        if date_from:
            try:
                start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        if date_to:
            try:
                end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Get analytics data
        analytics_data = {
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': get_summary_statistics(start_date, end_date),
            'trends': get_trend_analysis(start_date, end_date),
            'account_analysis': get_account_analysis(start_date, end_date),
            'user_activity': get_user_activity_analysis(start_date, end_date),
            'validation_insights': get_validation_insights(start_date, end_date),
        }
        
        context = {
            'page_title': 'لوحة التحليلات المحاسبية',
            'analytics_data': analytics_data,
            'date_from': start_date.isoformat(),
            'date_to': end_date.isoformat(),
        }
        
        return render(request, 'accounting/analytics_dashboard.html', context)
    
    except Exception as e:
        logger.error(f"Error in analytics dashboard: {str(e)}")
        return render(request, 'accounting/analytics_dashboard.html', {
            'page_title': 'لوحة التحليلات المحاسبية',
            'error': 'حدث خطأ في تحميل البيانات'
        })


@login_required
def journal_entries_report(request):
    """
    Comprehensive journal entries report with filtering
    """
    try:
        from .models import JournalEntry, Account
        
        # Get filters from request
        filters = {
            'date_from': request.GET.get('date_from'),
            'date_to': request.GET.get('date_to'),
            'account_id': request.GET.get('account_id'),
            'entry_type': request.GET.get('entry_type'),
            'status': request.GET.get('status'),
            'user_id': request.GET.get('user_id'),
            'search': request.GET.get('search'),
        }
        
        # Build queryset
        queryset = JournalEntry.objects.all()
        
        if filters['date_from']:
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass
        
        if filters['date_to']:
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass
        
        if filters['account_id']:
            try:
                account_id = int(filters['account_id'])
                queryset = queryset.filter(items__account_id=account_id).distinct()
            except (ValueError, TypeError):
                pass
        
        if filters['entry_type']:
            queryset = queryset.filter(entry_type=filters['entry_type'])
        
        if filters['status']:
            if filters['status'] == 'posted':
                queryset = queryset.filter(is_posted=True)
            elif filters['status'] == 'draft':
                queryset = queryset.filter(is_posted=False)
        
        if filters['user_id']:
            try:
                user_id = int(filters['user_id'])
                queryset = queryset.filter(created_by_id=user_id)
            except (ValueError, TypeError):
                pass
        
        if filters['search']:
            search_term = filters['search']
            queryset = queryset.filter(
                Q(description__icontains=search_term) |
                Q(number__icontains=search_term)
            )
        
        # Get statistics
        stats = queryset.aggregate(
            total_entries=Count('id'),
            total_debit=Sum('total_debit'),
            total_credit=Sum('total_credit'),
            avg_amount=Avg('total_debit')
        )
        
        # Pagination
        entries = queryset.select_related('created_by').order_by('-date', '-id')[:100]
        
        context = {
            'page_title': 'تقرير القيود المحاسبية',
            'entries': entries,
            'stats': stats,
            'filters': filters,
            'accounts': Account.objects.all()[:100],  # For filter dropdown
        }
        
        # Export functionality
        export_format = request.GET.get('export')
        if export_format == 'excel':
            return export_journal_entries_excel_report(queryset)
        elif export_format == 'pdf':
            return export_journal_entries_pdf_report(queryset)
        
        return render(request, 'accounting/journal_entries_report.html', context)
    
    except Exception as e:
        logger.error(f"Error in journal entries report: {str(e)}")
        return render(request, 'accounting/journal_entries_report.html', {
            'page_title': 'تقرير القيود المحاسبية',
            'error': 'حدث خطأ في تحميل التقرير'
        })


@login_required
def analytics_api(request):
    """
    API endpoint for analytics data (AJAX requests)
    """
    try:
        analysis_type = request.GET.get('type', 'summary')
        
        if analysis_type == 'summary':
            data = get_summary_statistics()
        elif analysis_type == 'trends':
            data = get_trend_analysis()
        elif analysis_type == 'accounts':
            data = get_account_analysis()
        elif analysis_type == 'performance':
            data = get_performance_metrics()
        else:
            data = {'error': 'نوع التحليل غير مدعوم'}
        
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f"Error in analytics API: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في تحميل البيانات'}, status=500)


def get_summary_statistics(start_date=None, end_date=None):
    """
    Get summary statistics for the dashboard
    """
    try:
        from .models import JournalEntry, Account
        
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Journal entries statistics
        entries_queryset = JournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        
        entries_stats = entries_queryset.aggregate(
            total_entries=Count('id'),
            total_debit=Sum('total_debit'),
            total_credit=Sum('total_credit'),
            posted_entries=Count('id', filter=Q(is_posted=True)),
            draft_entries=Count('id', filter=Q(is_posted=False))
        )
        
        # Account statistics
        accounts_stats = Account.objects.aggregate(
            total_accounts=Count('id'),
            active_accounts=Count('id', filter=Q(is_active=True)),
            asset_accounts=Count('id', filter=Q(type='asset')),
            liability_accounts=Count('id', filter=Q(type='liability')),
            equity_accounts=Count('id', filter=Q(type='equity')),
            revenue_accounts=Count('id', filter=Q(type='revenue')),
            expense_accounts=Count('id', filter=Q(type='expense'))
        )
        
        # Recent activity
        recent_entries = entries_queryset.order_by('-created_at')[:5]
        recent_activity = [
            {
                'id': entry.id,
                'number': entry.number,
                'description': entry.description[:50],
                'date': entry.date.isoformat() if entry.date else None,
                'amount': float(entry.total_debit or 0),
                'status': 'مرحّل' if entry.is_posted else 'مسودة'
            }
            for entry in recent_entries
        ]
        
        # Growth statistics (compared to previous period)
        previous_start = start_date - (end_date - start_date)
        previous_end = start_date
        
        previous_stats = JournalEntry.objects.filter(
            date__gte=previous_start,
            date__lt=previous_end
        ).aggregate(
            total_entries=Count('id'),
            total_amount=Sum('total_debit')
        )
        
        # Calculate growth
        current_entries = entries_stats['total_entries'] or 0
        previous_entries = previous_stats['total_entries'] or 0
        entries_growth = ((current_entries - previous_entries) / previous_entries * 100) if previous_entries > 0 else 0
        
        current_amount = float(entries_stats['total_debit'] or 0)
        previous_amount = float(previous_stats['total_amount'] or 0)
        amount_growth = ((current_amount - previous_amount) / previous_amount * 100) if previous_amount > 0 else 0
        
        return {
            'entries': {
                'total': entries_stats['total_entries'] or 0,
                'posted': entries_stats['posted_entries'] or 0,
                'draft': entries_stats['draft_entries'] or 0,
                'total_debit': float(entries_stats['total_debit'] or 0),
                'total_credit': float(entries_stats['total_credit'] or 0),
                'growth_percentage': round(entries_growth, 1)
            },
            'accounts': accounts_stats,
            'recent_activity': recent_activity,
            'growth': {
                'entries_growth': round(entries_growth, 1),
                'amount_growth': round(amount_growth, 1)
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting summary statistics: {str(e)}")
        return {
            'entries': {'total': 0, 'posted': 0, 'draft': 0, 'total_debit': 0, 'total_credit': 0},
            'accounts': {'total_accounts': 0},
            'recent_activity': [],
            'growth': {'entries_growth': 0, 'amount_growth': 0}
        }


def get_trend_analysis(start_date=None, end_date=None):
    """
    Get trend analysis data for charts
    """
    try:
        from .models import JournalEntry
        
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Daily trends
        daily_trends = JournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).extra(
            select={'day': 'date(date)'}
        ).values('day').annotate(
            entries_count=Count('id'),
            total_amount=Sum('total_debit')
        ).order_by('day')
        
        # Weekly trends
        weekly_trends = JournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).annotate(
            week=TruncWeek('date')
        ).values('week').annotate(
            entries_count=Count('id'),
            total_amount=Sum('total_debit')
        ).order_by('week')
        
        # Monthly trends (if date range is large enough)
        monthly_trends = JournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).annotate(
            month=TruncMonth('date')
        ).values('month').annotate(
            entries_count=Count('id'),
            total_amount=Sum('total_debit')
        ).order_by('month')
        
        return {
            'daily': [
                {
                    'date': trend['day'].isoformat() if trend['day'] else '',
                    'entries': trend['entries_count'],
                    'amount': float(trend['total_amount'] or 0)
                }
                for trend in daily_trends
            ],
            'weekly': [
                {
                    'week': trend['week'].isoformat() if trend['week'] else '',
                    'entries': trend['entries_count'],
                    'amount': float(trend['total_amount'] or 0)
                }
                for trend in weekly_trends
            ],
            'monthly': [
                {
                    'month': trend['month'].isoformat() if trend['month'] else '',
                    'entries': trend['entries_count'],
                    'amount': float(trend['total_amount'] or 0)
                }
                for trend in monthly_trends
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting trend analysis: {str(e)}")
        return {'daily': [], 'weekly': [], 'monthly': []}


def get_account_analysis(start_date=None, end_date=None):
    """
    Get account usage analysis
    """
    try:
        from .models import JournalEntryItem, Account
        
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Most used accounts
        most_used = JournalEntryItem.objects.filter(
            journal_entry__date__gte=start_date,
            journal_entry__date__lte=end_date
        ).values(
            'account__code',
            'account__name',
            'account__type'
        ).annotate(
            usage_count=Count('id'),
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        ).order_by('-usage_count')[:10]
        
        # Account types distribution
        account_types = Account.objects.values('type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Balance analysis by account type
        balance_by_type = JournalEntryItem.objects.filter(
            journal_entry__date__gte=start_date,
            journal_entry__date__lte=end_date
        ).values('account__type').annotate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit'),
            net_balance=Sum('debit') - Sum('credit')
        )
        
        return {
            'most_used_accounts': [
                {
                    'code': item['account__code'],
                    'name': item['account__name'],
                    'type': item['account__type'],
                    'usage_count': item['usage_count'],
                    'total_debit': float(item['total_debit'] or 0),
                    'total_credit': float(item['total_credit'] or 0)
                }
                for item in most_used
            ],
            'account_types_distribution': [
                {
                    'type': item['type'],
                    'count': item['count']
                }
                for item in account_types
            ],
            'balance_by_type': [
                {
                    'type': item['account__type'],
                    'total_debit': float(item['total_debit'] or 0),
                    'total_credit': float(item['total_credit'] or 0),
                    'net_balance': float(item['net_balance'] or 0)
                }
                for item in balance_by_type
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting account analysis: {str(e)}")
        return {
            'most_used_accounts': [],
            'account_types_distribution': [],
            'balance_by_type': []
        }


def get_user_activity_analysis(start_date=None, end_date=None):
    """
    Get user activity analysis
    """
    try:
        from .models import JournalEntry
        from django.contrib.auth.models import User
        
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # User activity statistics
        user_activity = JournalEntry.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            created_by__isnull=False
        ).values(
            'created_by__username',
            'created_by__first_name',
            'created_by__last_name'
        ).annotate(
            entries_created=Count('id'),
            total_amount=Sum('total_debit')
        ).order_by('-entries_created')[:10]
        
        return {
            'top_users': [
                {
                    'username': item['created_by__username'],
                    'full_name': f"{item['created_by__first_name']} {item['created_by__last_name']}".strip(),
                    'entries_created': item['entries_created'],
                    'total_amount': float(item['total_amount'] or 0)
                }
                for item in user_activity
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting user activity analysis: {str(e)}")
        return {'top_users': []}


def get_validation_insights(start_date=None, end_date=None):
    """
    Get validation and error insights
    """
    try:
        # This would integrate with the validation system to provide insights
        # For now, returning placeholder data
        return {
            'common_errors': [
                {'error': 'القيد غير متوازن', 'count': 15},
                {'error': 'حساب غير صحيح', 'count': 8},
                {'error': 'مبلغ غير صحيح', 'count': 5}
            ],
            'validation_success_rate': 87.5,
            'avg_validation_time': 0.234
        }
    
    except Exception as e:
        logger.error(f"Error getting validation insights: {str(e)}")
        return {
            'common_errors': [],
            'validation_success_rate': 0,
            'avg_validation_time': 0
        }


def get_performance_metrics():
    """
    Get performance metrics from middleware
    """
    try:
        from .middleware import get_performance_dashboard_data, get_error_dashboard_data
        
        return {
            'performance': get_performance_dashboard_data(),
            'errors': get_error_dashboard_data()
        }
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return {
            'performance': {'total_requests': 0, 'average_duration': 0},
            'errors': {'total_errors': 0}
        }


def export_journal_entries_excel_report(queryset):
    """
    Export journal entries report to Excel
    """
    try:
        import openpyxl
        from django.http import HttpResponse
        
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = 'Journal Entries Report'
        
        # Headers
        headers = ['رقم القيد', 'التاريخ', 'البيان', 'المدين', 'الدائن', 'الحالة', 'المستخدم']
        for col, header in enumerate(headers, 1):
            worksheet.cell(row=1, column=col, value=header)
        
        # Data
        for row, entry in enumerate(queryset[:1000], 2):  # Limit to 1000 rows
            worksheet.cell(row=row, column=1, value=entry.number)
            worksheet.cell(row=row, column=2, value=entry.date.isoformat() if entry.date else '')
            worksheet.cell(row=row, column=3, value=entry.description)
            worksheet.cell(row=row, column=4, value=float(entry.total_debit or 0))
            worksheet.cell(row=row, column=5, value=float(entry.total_credit or 0))
            worksheet.cell(row=row, column=6, value='مرحّل' if entry.is_posted else 'مسودة')
            worksheet.cell(row=row, column=7, value=str(entry.created_by) if entry.created_by else '')
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="journal_entries_report.xlsx"'
        
        workbook.save(response)
        return response
    
    except Exception as e:
        logger.error(f"Error exporting Excel report: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في تصدير التقرير'}, status=500)


def export_journal_entries_pdf_report(queryset):
    """
    Export journal entries report to PDF
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="journal_entries_report.pdf"'
        
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        
        # Title
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, "Journal Entries Report")
        
        # Headers
        p.setFont("Helvetica-Bold", 10)
        y = height - 100
        p.drawString(50, y, "Number")
        p.drawString(120, y, "Date")
        p.drawString(200, y, "Description")
        p.drawString(350, y, "Debit")
        p.drawString(420, y, "Credit")
        p.drawString(490, y, "Status")
        
        # Data
        p.setFont("Helvetica", 8)
        for entry in queryset[:50]:  # Limit to 50 entries for PDF
            y -= 20
            if y < 50:  # New page
                p.showPage()
                y = height - 50
            
            p.drawString(50, y, entry.number or '')
            p.drawString(120, y, entry.date.strftime('%Y-%m-%d') if entry.date else '')
            p.drawString(200, y, (entry.description or '')[:20])
            p.drawString(350, y, str(entry.total_debit or 0))
            p.drawString(420, y, str(entry.total_credit or 0))
            p.drawString(490, y, 'Posted' if entry.is_posted else 'Draft')
        
        p.showPage()
        p.save()
        
        return response
    
    except Exception as e:
        logger.error(f"Error exporting PDF report: {str(e)}")
        return JsonResponse({'error': 'حدث خطأ في تصدير التقرير'}, status=500)