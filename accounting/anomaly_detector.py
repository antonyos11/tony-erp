"""
نظام الكشف عن الشذوذ في القيود المحاسبية
Accounting Anomaly Detection System
"""

from django.db.models import Sum, Avg, Count, Q, F
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
import statistics


class AnomalyDetector:
    """كاشف الشذوذ في القيود المحاسبية"""
    
    # عتبات الكشف
    THRESHOLDS = {
        'amount_deviation': 3,  # 3 انحرافات معيارية
        'frequency_deviation': 2.5,
        'time_deviation': 2,
        'duplicate_similarity': 0.95,  # 95% تشابه
    }
    
    def __init__(self, start_date=None, end_date=None):
        self.start_date = start_date or (timezone.now() - timedelta(days=30)).date()
        self.end_date = end_date or timezone.now().date()
    
    def detect_all_anomalies(self):
        """كشف جميع أنواع الشذوذ"""
        anomalies = {
            'unusual_amounts': self.detect_unusual_amounts(),
            'duplicate_entries': self.detect_duplicate_entries(),
            'unusual_timing': self.detect_unusual_timing(),
            'unbalanced_entries': self.detect_unbalanced_entries(),
            'unusual_accounts': self.detect_unusual_account_usage(),
            'sequential_anomalies': self.detect_sequential_anomalies(),
        }
        
        return anomalies
    
    def detect_unusual_amounts(self):
        """كشف المبالغ غير الاعتيادية"""
        from accounting.models import JournalEntry, JournalEntryItem
        
        # حساب الإحصائيات
        items = JournalEntryItem.objects.filter(
            entry__entry_date__range=[self.start_date, self.end_date],
            entry__status='approved'
        )
        
        amounts = list(items.values_list('debit_amount', flat=True)) + \
                 list(items.values_list('credit_amount', flat=True))
        amounts = [float(a) for a in amounts if a > 0]
        
        if len(amounts) < 10:
            return []
        
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        
        # كشف القيم الشاذة
        threshold = mean + (self.THRESHOLDS['amount_deviation'] * stdev)
        
        unusual_items = items.filter(
            Q(debit_amount__gt=threshold) | Q(credit_amount__gt=threshold)
        ).select_related('entry', 'account')
        
        anomalies = []
        for item in unusual_items:
            amount = item.debit_amount if item.debit_amount > 0 else item.credit_amount
            deviation = (float(amount) - mean) / stdev if stdev > 0 else 0
            
            anomalies.append({
                'type': 'unusual_amount',
                'severity': 'high' if deviation > 4 else 'medium',
                'entry_id': item.entry.id,
                'entry_number': item.entry.entry_number,
                'date': item.entry.entry_date,
                'account': item.account.name,
                'amount': float(amount),
                'mean': round(mean, 2),
                'deviation': round(deviation, 2),
                'description': f'مبلغ غير اعتيادي: {amount:,.2f} ج.م (المتوسط: {mean:,.2f})',
            })
        
        return anomalies
    
    def detect_duplicate_entries(self):
        """كشف القيود المكررة"""
        from accounting.models import JournalEntry
        
        entries = JournalEntry.objects.filter(
            entry_date__range=[self.start_date, self.end_date],
            status='approved'
        ).prefetch_related('items')
        
        duplicates = []
        checked = set()
        
        for entry in entries:
            if entry.id in checked:
                continue
            
            # البحث عن قيود مشابهة
            similar = entries.filter(
                entry_date=entry.entry_date,
                description=entry.description,
                total_amount=entry.total_amount
            ).exclude(id=entry.id)
            
            for similar_entry in similar:
                if similar_entry.id in checked:
                    continue
                
                # التحقق من تشابه البنود
                similarity = self._calculate_entry_similarity(entry, similar_entry)
                
                if similarity >= self.THRESHOLDS['duplicate_similarity']:
                    duplicates.append({
                        'type': 'duplicate_entry',
                        'severity': 'high' if similarity > 0.98 else 'medium',
                        'entry_id': entry.id,
                        'entry_number': entry.entry_number,
                        'duplicate_id': similar_entry.id,
                        'duplicate_number': similar_entry.entry_number,
                        'date': entry.entry_date,
                        'amount': float(entry.total_amount),
                        'similarity': round(similarity * 100, 2),
                        'description': f'قيد مكرر محتمل: {entry.entry_number} و {similar_entry.entry_number}',
                    })
                    
                    checked.add(entry.id)
                    checked.add(similar_entry.id)
        
        return duplicates
    
    def _calculate_entry_similarity(self, entry1, entry2):
        """حساب نسبة التشابه بين قيدين"""
        items1 = set((item.account_id, float(item.debit_amount), float(item.credit_amount)) 
                     for item in entry1.items.all())
        items2 = set((item.account_id, float(item.debit_amount), float(item.credit_amount)) 
                     for item in entry2.items.all())
        
        if not items1 or not items2:
            return 0
        
        common = items1 & items2
        total = items1 | items2
        
        return len(common) / len(total) if total else 0
    
    def detect_unusual_timing(self):
        """كشف القيود في أوقات غير اعتيادية"""
        from accounting.models import JournalEntry
        from django.db.models.functions import ExtractHour, ExtractWeekDay
        
        # القيود في ساعات غير العمل (قبل 6 صباحاً أو بعد 10 مساءً)
        unusual_hours = JournalEntry.objects.filter(
            entry_date__range=[self.start_date, self.end_date],
            status='approved'
        ).annotate(
            hour=ExtractHour('created_at')
        ).filter(
            Q(hour__lt=6) | Q(hour__gt=22)
        )
        
        # القيود في أيام العطلات (الجمعة والسبت)
        weekend_entries = JournalEntry.objects.filter(
            entry_date__range=[self.start_date, self.end_date],
            status='approved'
        ).annotate(
            weekday=ExtractWeekDay('entry_date')
        ).filter(
            weekday__in=[6, 7]  # الجمعة والسبت
        )
        
        anomalies = []
        
        for entry in unusual_hours:
            hour = entry.created_at.hour
            anomalies.append({
                'type': 'unusual_timing',
                'severity': 'medium',
                'entry_id': entry.id,
                'entry_number': entry.entry_number,
                'date': entry.entry_date,
                'created_at': entry.created_at,
                'hour': hour,
                'description': f'قيد تم إنشاؤه في وقت غير اعتيادي: الساعة {hour}',
            })
        
        for entry in weekend_entries:
            anomalies.append({
                'type': 'weekend_entry',
                'severity': 'low',
                'entry_id': entry.id,
                'entry_number': entry.entry_number,
                'date': entry.entry_date,
                'description': f'قيد تم إنشاؤه في عطلة نهاية الأسبوع',
            })
        
        return anomalies
    
    def detect_unbalanced_entries(self):
        """كشف القيود غير المتوازنة"""
        from accounting.models import JournalEntry
        
        entries = JournalEntry.objects.filter(
            entry_date__range=[self.start_date, self.end_date],
            status='approved'
        ).prefetch_related('items')
        
        unbalanced = []
        
        for entry in entries:
            total_debits = sum(item.debit_amount for item in entry.items.all())
            total_credits = sum(item.credit_amount for item in entry.items.all())
            
            difference = abs(total_debits - total_credits)
            
            if difference > Decimal('0.01'):  # فرق أكبر من قرش واحد
                unbalanced.append({
                    'type': 'unbalanced_entry',
                    'severity': 'high',
                    'entry_id': entry.id,
                    'entry_number': entry.entry_number,
                    'date': entry.entry_date,
                    'total_debits': float(total_debits),
                    'total_credits': float(total_credits),
                    'difference': float(difference),
                    'description': f'قيد غير متوازن: فرق {difference:,.2f} ج.م',
                })
        
        return unbalanced
    
    def detect_unusual_account_usage(self):
        """كشف استخدام حسابات بشكل غير اعتيادي"""
        from accounting.models import JournalEntryItem, Account
        
        # حساب تكرار استخدام كل حساب
        account_usage = JournalEntryItem.objects.filter(
            entry__entry_date__range=[self.start_date, self.end_date],
            entry__status='approved'
        ).values('account').annotate(
            count=Count('id'),
            total_debit=Sum('debit_amount'),
            total_credit=Sum('credit_amount')
        )
        
        counts = [item['count'] for item in account_usage if item['count'] > 0]
        
        if len(counts) < 5:
            return []
        
        mean = statistics.mean(counts)
        stdev = statistics.stdev(counts)
        
        threshold_high = mean + (self.THRESHOLDS['frequency_deviation'] * stdev)
        threshold_low = mean - (self.THRESHOLDS['frequency_deviation'] * stdev)
        
        anomalies = []
        
        for item in account_usage:
            account = Account.objects.get(id=item['account'])
            
            if item['count'] > threshold_high:
                anomalies.append({
                    'type': 'overused_account',
                    'severity': 'medium',
                    'account_id': account.id,
                    'account_name': account.name,
                    'usage_count': item['count'],
                    'expected_count': round(mean, 0),
                    'description': f'حساب مستخدم بشكل مفرط: {account.name} ({item["count"]} مرة)',
                })
            elif item['count'] < threshold_low and item['count'] > 0:
                anomalies.append({
                    'type': 'underused_account',
                    'severity': 'low',
                    'account_id': account.id,
                    'account_name': account.name,
                    'usage_count': item['count'],
                    'expected_count': round(mean, 0),
                    'description': f'حساب مستخدم بشكل نادر: {account.name} ({item["count"]} مرة)',
                })
        
        return anomalies
    
    def detect_sequential_anomalies(self):
        """كشف الشذوذ في تسلسل القيود"""
        from accounting.models import JournalEntry
        
        entries = JournalEntry.objects.filter(
            entry_date__range=[self.start_date, self.end_date],
            status='approved'
        ).order_by('entry_date', 'created_at')
        
        anomalies = []
        prev_entry = None
        
        for entry in entries:
            if prev_entry:
                # فحص التسلسل الزمني
                if entry.entry_date < prev_entry.entry_date:
                    anomalies.append({
                        'type': 'date_sequence',
                        'severity': 'medium',
                        'entry_id': entry.id,
                        'entry_number': entry.entry_number,
                        'date': entry.entry_date,
                        'prev_entry': prev_entry.entry_number,
                        'prev_date': prev_entry.entry_date,
                        'description': f'قيد بتاريخ سابق للقيد السابق',
                    })
                
                # فحص القفزات الكبيرة في المبالغ
                amount_diff = abs(float(entry.total_amount - prev_entry.total_amount))
                if prev_entry.total_amount > 0:
                    percent_diff = (amount_diff / float(prev_entry.total_amount)) * 100
                    
                    if percent_diff > 500:  # زيادة أكثر من 500%
                        anomalies.append({
                            'type': 'amount_jump',
                            'severity': 'medium',
                            'entry_id': entry.id,
                            'entry_number': entry.entry_number,
                            'amount': float(entry.total_amount),
                            'prev_amount': float(prev_entry.total_amount),
                            'percent_diff': round(percent_diff, 2),
                            'description': f'قفزة كبيرة في المبلغ: {percent_diff:.0f}% عن القيد السابق',
                        })
            
            prev_entry = entry
        
        return anomalies
    
    def generate_report(self):
        """إنشاء تقرير شامل عن الشذوذ"""
        all_anomalies = self.detect_all_anomalies()
        
        # حساب الإحصائيات
        total_count = sum(len(anomalies) for anomalies in all_anomalies.values())
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        
        for category, anomalies in all_anomalies.items():
            for anomaly in anomalies:
                severity_counts[anomaly.get('severity', 'low')] += 1
        
        report = {
            'period': {
                'start_date': self.start_date,
                'end_date': self.end_date,
            },
            'summary': {
                'total_anomalies': total_count,
                'high_severity': severity_counts['high'],
                'medium_severity': severity_counts['medium'],
                'low_severity': severity_counts['low'],
            },
            'anomalies': all_anomalies,
            'recommendations': self._generate_recommendations(all_anomalies),
        }
        
        return report
    
    def _generate_recommendations(self, anomalies):
        """إنشاء توصيات بناءً على الشذوذ المكتشف"""
        recommendations = []
        
        if anomalies['unbalanced_entries']:
            recommendations.append({
                'priority': 'high',
                'message': 'يوجد قيود غير متوازنة تحتاج إلى مراجعة فورية',
                'action': 'مراجعة وتصحيح القيود غير المتوازنة'
            })
        
        if anomalies['duplicate_entries']:
            recommendations.append({
                'priority': 'high',
                'message': 'يوجد قيود مكررة محتملة',
                'action': 'مراجعة القيود المكررة وحذف الزائد منها'
            })
        
        if anomalies['unusual_amounts']:
            recommendations.append({
                'priority': 'medium',
                'message': 'يوجد قيود بمبالغ غير اعتيادية',
                'action': 'التحقق من صحة المبالغ الكبيرة'
            })
        
        if anomalies['unusual_timing']:
            recommendations.append({
                'priority': 'medium',
                'message': 'يوجد قيود تم إنشاؤها في أوقات غير اعتيادية',
                'action': 'مراجعة القيود التي تمت في أوقات غير العمل'
            })
        
        return recommendations
