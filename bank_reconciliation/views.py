"""
Views مطابقة البنوك
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import csv
import io

from .models import BankStatement, BankStatementLine, Reconciliation, ReconciliationItem
from .forms import BankStatementUploadForm, ReconciliationForm


@login_required
def reconciliation_dashboard(request):
    """لوحة تحكم المطابقة"""
    pending_statements = BankStatement.objects.filter(status='pending').count()
    in_progress = Reconciliation.objects.filter(status='in_progress').count()
    completed = Reconciliation.objects.filter(status='completed').count()
    
    recent_reconciliations = Reconciliation.objects.select_related('bank_account').order_by('-created_at')[:10]
    recent_statements = BankStatement.objects.select_related('bank_account').order_by('-imported_at')[:10]
    
    return render(request, 'bank_reconciliation/dashboard.html', {
        'pending_statements': pending_statements,
        'in_progress': in_progress,
        'completed': completed,
        'recent_reconciliations': recent_reconciliations,
        'recent_statements': recent_statements,
        'page_title': 'مطابقة البنوك',
    })


@login_required
def statement_list(request):
    """قائمة كشوف الحسابات"""
    statements = BankStatement.objects.select_related('bank_account', 'imported_by').all()
    paginator = Paginator(statements, 20)
    statements = paginator.get_page(request.GET.get('page'))
    return render(request, 'bank_reconciliation/statement_list.html', {
        'statements': statements,
        'page_title': 'كشوف الحسابات البنكية',
    })


@login_required
def statement_upload(request):
    """رفع كشف حساب"""
    if request.method == 'POST':
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            statement = form.save(commit=False)
            statement.imported_by = request.user
            statement.save()
            messages.success(request, 'تم رفع الكشف بنجاح')
            return redirect('bank_reconciliation:statement_detail', pk=statement.pk)
    else:
        form = BankStatementUploadForm()
    return render(request, 'bank_reconciliation/statement_upload.html', {
        'form': form,
        'page_title': 'رفع كشف حساب بنكي',
    })


@login_required
def statement_detail(request, pk):
    """تفاصيل كشف الحساب"""
    statement = get_object_or_404(BankStatement.objects.select_related('bank_account'), pk=pk)
    lines = statement.transactions.all()
    return render(request, 'bank_reconciliation/statement_detail.html', {
        'statement': statement,
        'lines': lines,
        'page_title': f'كشف حساب: {statement.bank_account}',
    })


@login_required
def statement_import_csv(request, pk):
    """استيراد بيانات من CSV"""
    statement = get_object_or_404(BankStatement, pk=pk)
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded = csv_file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        
        count = 0
        for row in reader:
            BankStatementLine.objects.create(
                statement=statement,
                transaction_date=row.get('date', row.get('التاريخ', '')),
                description=row.get('description', row.get('الوصف', '')),
                debit=Decimal(row.get('debit', row.get('مدين', '0')) or '0'),
                credit=Decimal(row.get('credit', row.get('دائن', '0')) or '0'),
                reference=row.get('reference', row.get('المرجع', '')),
            )
            count += 1
        
        statement.status = 'in_progress'
        statement.save()
        messages.success(request, f'تم استيراد {count} حركة بنجاح')
        return redirect('bank_reconciliation:statement_detail', pk=pk)
    
    return render(request, 'bank_reconciliation/statement_import.html', {
        'statement': statement,
        'page_title': 'استيراد بيانات CSV',
    })


@login_required
def auto_match(request, pk):
    """المطابقة التلقائية"""
    statement = get_object_or_404(BankStatement, pk=pk)
    
    matched_count = 0
    for line in statement.transactions.filter(is_matched=False):
        # البحث عن قيد مطابق بنفس المبلغ والتاريخ
        from accounting.models import JournalEntry
        
        amount = abs(line.amount)
        matching_entries = JournalEntry.objects.filter(
            date__gte=line.transaction_date - timezone.timedelta(days=3),
            date__lte=line.transaction_date + timezone.timedelta(days=3),
        ).filter(
            Q(lines__debit=amount) | Q(lines__credit=amount)
        ).distinct()
        
        if matching_entries.count() == 1:
            line.matched_entry = matching_entries.first()
            line.is_matched = True
            line.matched_at = timezone.now()
            line.matched_by = request.user
            line.save()
            matched_count += 1
    
    messages.success(request, f'تم مطابقة {matched_count} حركة تلقائياً')
    return redirect('bank_reconciliation:statement_detail', pk=pk)


@login_required
def manual_match(request, line_id):
    """المطابقة اليدوية"""
    line = get_object_or_404(BankStatementLine, pk=line_id)
    
    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        if entry_id:
            from accounting.models import JournalEntry
            entry = get_object_or_404(JournalEntry, pk=entry_id)
            line.matched_entry = entry
            line.is_matched = True
            line.matched_at = timezone.now()
            line.matched_by = request.user
            line.save()
            messages.success(request, 'تمت المطابقة بنجاح')
        return redirect('bank_reconciliation:statement_detail', pk=line.statement.pk)
    
    # البحث عن قيود محتملة
    from accounting.models import JournalEntry
    suggestions = JournalEntry.objects.filter(
        date__gte=line.transaction_date - timezone.timedelta(days=7),
        date__lte=line.transaction_date + timezone.timedelta(days=7),
    ).order_by('-date')[:20]
    
    return render(request, 'bank_reconciliation/manual_match.html', {
        'line': line,
        'suggestions': suggestions,
        'page_title': 'المطابقة اليدوية',
    })


@login_required
def reconciliation_list(request):
    """قائمة المطابقات"""
    reconciliations = Reconciliation.objects.select_related('bank_account', 'created_by').all()
    paginator = Paginator(reconciliations, 20)
    reconciliations = paginator.get_page(request.GET.get('page'))
    return render(request, 'bank_reconciliation/reconciliation_list.html', {
        'reconciliations': reconciliations,
        'page_title': 'المطابقات البنكية',
    })


@login_required
def reconciliation_create(request):
    """إنشاء مطابقة جديدة"""
    if request.method == 'POST':
        form = ReconciliationForm(request.POST)
        if form.is_valid():
            recon = form.save(commit=False)
            recon.created_by = request.user
            recon.difference = recon.bank_balance - recon.book_balance
            recon.save()
            messages.success(request, 'تم إنشاء المطابقة بنجاح')
            return redirect('bank_reconciliation:reconciliation_detail', pk=recon.pk)
    else:
        form = ReconciliationForm()
    return render(request, 'bank_reconciliation/reconciliation_form.html', {
        'form': form,
        'page_title': 'إنشاء مطابقة جديدة',
    })


@login_required
def reconciliation_detail(request, pk):
    """تفاصيل المطابقة"""
    recon = get_object_or_404(Reconciliation.objects.select_related('bank_account'), pk=pk)
    items = recon.items.all()
    return render(request, 'bank_reconciliation/reconciliation_detail.html', {
        'reconciliation': recon,
        'items': items,
        'page_title': f'مطابقة: {recon.bank_account}',
    })


@login_required
def reconciliation_report(request):
    """تقرير المطابقات"""
    reconciliations = Reconciliation.objects.select_related('bank_account').all()
    stats = reconciliations.aggregate(
        total=Count('id'),
        total_diff=Sum('difference'),
    )
    return render(request, 'bank_reconciliation/reports/reconciliation_report.html', {
        'reconciliations': reconciliations,
        'stats': stats,
        'page_title': 'تقرير المطابقات',
    })
