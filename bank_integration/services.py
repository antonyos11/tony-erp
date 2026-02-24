"""
خدمات التكامل البنكي
Bank Integration Services
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Q, Sum
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

from .models import (
    BankAccount, BankTransaction, BankReconciliation, 
    BankTransactionMapping, BankFee
)
from accounting.models import JournalEntry, Account
from payments.models import PaymentTransaction

logger = logging.getLogger(__name__)


class BankSyncService:
    """خدمة مزامنة العمليات البنكية"""
    
    def sync_account_transactions(self, account: BankAccount):
        """مزامنة عمليات حساب بنكي"""
        try:
            if not account.sync_enabled:
                return {'success': False, 'message': 'المزامنة غير مفعلة'}
            
            # هنا يتم الاتصال بـ API البنك
            transactions_data = self._fetch_from_bank_api(account)
            
            created_count = 0
            updated_count = 0
            
            for trans_data in transactions_data:
                bank_trans, created = BankTransaction.objects.get_or_create(
                    account=account,
                    reference_number=trans_data['reference_number'],
                    defaults={
                        'transaction_date': trans_data['transaction_date'],
                        'value_date': trans_data.get('value_date'),
                        'amount': Decimal(str(trans_data['amount'])),
                        'transaction_type': trans_data['type'],
                        'description': trans_data['description'],
                        'bank_reference': trans_data.get('bank_reference', ''),
                        'counterparty_name': trans_data.get('counterparty_name', ''),
                        'counterparty_account': trans_data.get('counterparty_account', ''),
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            
            # تحديث آخر مزامنة
            account.last_sync = timezone.now()
            account.save()
            
            return {
                'success': True,
                'created': created_count,
                'updated': updated_count,
                'total': len(transactions_data)
            }
            
        except Exception as e:
            logger.error(f"خطأ في مزامنة العمليات: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _fetch_from_bank_api(self, account: BankAccount):
        """جلب العمليات من API البنك"""
        # هذا مثال توضيحي - يجب تعديله حسب API البنك الفعلي
        return []
    
    def sync_all_accounts(self):
        """مزامنة جميع الحسابات النشطة"""
        accounts = BankAccount.objects.filter(status='active', sync_enabled=True)
        results = []
        
        for account in accounts:
            result = self.sync_account_transactions(account)
            results.append({
                'account': str(account),
                'result': result
            })
        
        return results


class ReconciliationService:
    """خدمة المطابقة البنكية"""
    
    def auto_reconcile(self, account: BankAccount, statement_date: datetime = None):
        """مطابقة تلقائية للعمليات"""
        if statement_date is None:
            statement_date = timezone.now().date()
        
        try:
            # الحصول على العمليات غير المتطابقة
            unreconciled = BankTransaction.objects.filter(
                account=account,
                status='pending',
                transaction_date__lte=statement_date
            )
            
            reconciliation = BankReconciliation.objects.create(
                account=account,
                statement_date=statement_date,
                statement_balance=account.current_balance,
                system_balance=self._get_system_balance(account, statement_date),
                status='in_progress'
            )
            
            matched_count = 0
            
            for trans in unreconciled:
                match = self._find_matching_entry(trans)
                
                if match:
                    self._create_mapping(trans, match['entry'], match['confidence'])
                    trans.status = 'reconciled'
                    trans.matched_invoice = match.get('invoice')
                    trans.matched_payment = match.get('payment')
                    trans.matching_score = match['confidence']
                    trans.save()
                    
                    reconciliation.reconciled_transactions.add(trans)
                    matched_count += 1
                else:
                    reconciliation.unreconciled_transactions.add(trans)
            
            reconciliation.calculate_difference()
            
            if reconciliation.difference == 0:
                reconciliation.status = 'completed'
            else:
                reconciliation.status = 'in_progress'
            
            reconciliation.save()
            
            return {
                'success': True,
                'reconciliation_id': str(reconciliation.id),
                'matched': matched_count,
                'unmatched': unreconciled.count() - matched_count,
                'difference': str(reconciliation.difference)
            }
            
        except Exception as e:
            logger.error(f"خطأ في المطابقة التلقائية: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def manual_reconcile(self, bank_transaction: BankTransaction, journal_entry: JournalEntry):
        """مطابقة يدوية"""
        self._create_mapping(bank_transaction, journal_entry, Decimal('100.00'))
        bank_transaction.status = 'reconciled'
        bank_transaction.save()
        return True
    
    def _find_matching_entry(self, transaction: BankTransaction):
        """البحث عن قيد محاسبي مطابق"""
        # البحث بناءً على المبلغ والتاريخ والوصف
        entries = JournalEntry.objects.filter(
            Q(amount=transaction.amount) |
            Q(amount=abs(transaction.amount))
        ).filter(
            entry_date__range=[
                transaction.transaction_date - timedelta(days=3),
                transaction.transaction_date + timedelta(days=3)
            ]
        )
        
        if entries.exists():
            return {
                'entry': entries.first(),
                'confidence': Decimal('85.00'),
                'invoice': None,
                'payment': None
            }
        
        return None
    
    def _create_mapping(self, transaction: BankTransaction, entry: JournalEntry, confidence: Decimal):
        """إنشاء ربط بين عملية بنكية وقيد محاسبي"""
        BankTransactionMapping.objects.create(
            bank_transaction=transaction,
            journal_entry=entry,
            matching_confidence=confidence,
            auto_matched=True
        )
    
    def _get_system_balance(self, account: BankAccount, statement_date: datetime):
        """حساب رصيد النظام"""
        initial_balance = Decimal('0')
        
        transactions = BankTransaction.objects.filter(
            account=account,
            transaction_date__lte=statement_date,
            status__in=['completed', 'reconciled']
        )
        
        for trans in transactions:
            if trans.transaction_type in ['credit', 'deposit']:
                initial_balance += trans.amount
            else:
                initial_balance -= trans.amount
        
        return initial_balance


class BankAnalyticsService:
    """خدمة تحليل العمليات البنكية"""
    
    def get_account_summary(self, account: BankAccount):
        """ملخص حساب بنكي"""
        transactions = BankTransaction.objects.filter(account=account)
        
        return {
            'total_transactions': transactions.count(),
            'total_inflows': transactions.filter(
                transaction_type__in=['credit', 'deposit']
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'total_outflows': transactions.filter(
                transaction_type__in=['debit', 'transfer', 'fee']
            ).aggregate(Sum('amount'))['amount__sum'] or 0,
            'average_transaction': (transactions.aggregate(Sum('amount'))['amount__sum'] or 0) / max(transactions.count(), 1),
            'last_sync': account.last_sync,
            'current_balance': account.current_balance,
            'pending_transactions': transactions.filter(status='pending').count(),
        }
    
    def get_reconciliation_report(self, account: BankAccount, months: int = 6):
        """تقرير المطابقة"""
        reconciliations = BankReconciliation.objects.filter(
            account=account,
            statement_date__gte=timezone.now().date() - timedelta(days=30 * months)
        ).order_by('-statement_date')
        
        total_reconciled = sum(r.reconciled_transactions.count() for r in reconciliations)
        total_unreconciled = sum(r.unreconciled_transactions.count() for r in reconciliations)
        average_difference = (sum(abs(r.difference) for r in reconciliations) / 
                            max(reconciliations.count(), 1))
        
        return {
            'total_reconciliations': reconciliations.count(),
            'total_reconciled_transactions': total_reconciled,
            'total_unreconciled_transactions': total_unreconciled,
            'average_variance': average_difference,
            'recent_reconciliations': list(reconciliations[:10].values())
        }
    
    def detect_anomalies(self, account: BankAccount):
        """اكتشاف العمليات الشاذة"""
        transactions = BankTransaction.objects.filter(account=account)
        
        avg_amount = (transactions.aggregate(Sum('amount'))['amount__sum'] or 0) / max(transactions.count(), 1)
        std_dev = self._calculate_std_dev(transactions, avg_amount)
        
        anomalies = []
        threshold = avg_amount + (2 * std_dev)
        
        for trans in transactions:
            if trans.amount > threshold:
                anomalies.append({
                    'transaction': str(trans),
                    'amount': trans.amount,
                    'threshold': threshold,
                    'deviation': ((trans.amount - avg_amount) / avg_amount) * 100 if avg_amount != 0 else 0
                })
        
        return anomalies
    
    def _calculate_std_dev(self, transactions, mean):
        """حساب الانحراف المعياري"""
        if transactions.count() <= 1:
            return 0
        
        variance = sum((trans.amount - mean) ** 2 for trans in transactions) / (transactions.count() - 1)
        return variance ** 0.5


# إنشاء instances
bank_sync_service = BankSyncService()
reconciliation_service = ReconciliationService()
bank_analytics_service = BankAnalyticsService()
