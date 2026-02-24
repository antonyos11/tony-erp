"""
تقرير الالتزامات القادمة (قروض + شيكات)
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


@login_required
def obligations_report(request):
    """تقرير الالتزامات القادمة (قروض + شيكات)"""
    
    # الفترة (افتراضي: 3 أشهر قادمة)
    period = int(request.GET.get('period', 90))  # بالأيام
    today = timezone.now().date()
    end_date = today + timedelta(days=period)
    
    # 1. القروض
    from accounting.models import Loan, LoanPayment
    
    active_loans = Loan.objects.filter(
        status='active'
    ).select_related('bank')
    
    loans_summary = {
        'total_principal': Decimal('0'),
        'total_outstanding': Decimal('0'),
        'monthly_payment': Decimal('0'),
        'loans': []
    }
    
    for loan in active_loans:
        loans_summary['total_principal'] += loan.principal_amount or Decimal('0')
        loans_summary['total_outstanding'] += loan.outstanding_balance or Decimal('0')
        loans_summary['monthly_payment'] += loan.monthly_payment or Decimal('0')
        
        # الأقساط القادمة
        upcoming_payments = LoanPayment.objects.filter(
            loan=loan,
            payment_date__range=[today, end_date]
        ).order_by('payment_date')
        
        loans_summary['loans'].append({
            'loan': loan,
            'upcoming_payments': upcoming_payments
        })
    
    # 2. الشيكات
    from accounting.models import Cheque
    
    # الشيكات الصادرة (التزامات علينا)
    outgoing_cheques = Cheque.objects.filter(
        cheque_type='outgoing',
        status__in=['pending', 'deposited'],
        due_date__range=[today, end_date]
    ).select_related('account').order_by('due_date')
    
    outgoing_total = outgoing_cheques.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # الشيكات الواردة (حقوق لنا)
    incoming_cheques = Cheque.objects.filter(
        cheque_type='incoming',
        status__in=['pending', 'deposited'],
        due_date__range=[today, end_date]
    ).order_by('due_date')
    
    incoming_total = incoming_cheques.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    # 3. الخلاصة
    total_obligations = loans_summary['monthly_payment'] * (period / 30) + outgoing_total
    net_cash_flow = incoming_total - outgoing_total
    
    # 4. تجميع حسب الشهر
    from collections import defaultdict
    obligations_by_month = defaultdict(lambda: {
        'loans': Decimal('0'),
        'cheques': Decimal('0'),
        'total': Decimal('0')
    })
    
    # قروض حسب الشهر
    for loan_data in loans_summary['loans']:
        for payment in loan_data['upcoming_payments']:
            month_key = payment.payment_date.strftime('%Y-%m')
            obligations_by_month[month_key]['loans'] += payment.principal_amount or Decimal('0')
    
    # شيكات حسب الشهر
    for cheque in outgoing_cheques:
        month_key = cheque.due_date.strftime('%Y-%m')
        obligations_by_month[month_key]['cheques'] += cheque.amount or Decimal('0')
    
    # حساب الإجمالي
    for month in obligations_by_month:
        obligations_by_month[month]['total'] = (
            obligations_by_month[month]['loans'] + 
            obligations_by_month[month]['cheques']
        )
    
    # تحويل إلى قائمة مرتبة
    obligations_timeline = sorted([
        {
            'month': month,
            'loans': data['loans'],
            'cheques': data['cheques'],
            'total': data['total']
        }
        for month, data in obligations_by_month.items()
    ], key=lambda x: x['month'])
    
    context = {
        'period': period,
        'today': today,
        'end_date': end_date,
        'loans_summary': loans_summary,
        'outgoing_cheques': outgoing_cheques,
        'incoming_cheques': incoming_cheques,
        'outgoing_total': outgoing_total,
        'incoming_total': incoming_total,
        'total_obligations': total_obligations,
        'net_cash_flow': net_cash_flow,
        'obligations_timeline': obligations_timeline,
    }
    
    return render(request, 'accounting/obligations_report.html', context)

