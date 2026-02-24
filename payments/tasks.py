"""
مهام Celery لتطبيق المدفوعات
"""
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import LoanInstallment, PaymentReminder
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_payment_reminders():
    """إرسال تذكيرات الدفع للأقساط المستحقة"""
    try:
        logger.info("بدء إرسال تذكيرات الدفع")
        
        # البحث عن الأقساط المستحقة خلال الأيام القادمة
        upcoming_date = timezone.now().date() + timezone.timedelta(days=3)
        overdue_date = timezone.now().date()
        
        # الأقساط المستحقة قريباً
        upcoming_installments = LoanInstallment.objects.filter(
            due_date__lte=upcoming_date,
            due_date__gte=overdue_date,
            status__in=['pending', 'partially_paid']
        )
        
        # الأقساط المتأخرة
        overdue_installments = LoanInstallment.objects.filter(
            due_date__lt=overdue_date,
            status__in=['pending', 'partially_paid']
        )
        
        reminders_sent = 0
        
        # إرسال تذكيرات للأقساط المستحقة قريباً
        for installment in upcoming_installments:
            reminder_sent = send_installment_reminder(
                installment, 
                reminder_type='upcoming'
            )
            if reminder_sent:
                reminders_sent += 1
        
        # إرسال تذكيرات للأقساط المتأخرة
        for installment in overdue_installments:
            reminder_sent = send_installment_reminder(
                installment, 
                reminder_type='overdue'
            )
            if reminder_sent:
                reminders_sent += 1
        
        logger.info(f"تم إرسال {reminders_sent} تذكير دفع")
        return f"تم إرسال {reminders_sent} تذكير دفع"
        
    except Exception as e:
        logger.error(f"خطأ في إرسال تذكيرات الدفع: {str(e)}")
        raise


def send_installment_reminder(installment, reminder_type='upcoming'):
    """إرسال تذكير لقسط محدد"""
    try:
        # التحقق من عدم إرسال تذكير مؤخراً
        recent_reminder = PaymentReminder.objects.filter(
            installment=installment,
            reminder_type=reminder_type,
            sent_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).exists()
        
        if recent_reminder:
            return False
        
        # إنشاء وحفظ سجل التذكير
        reminder = PaymentReminder.objects.create(
            installment=installment,
            reminder_type=reminder_type,
            scheduled_date=timezone.now().date(),
            status='pending'
        )
        
        # إعداد محتوى الرسالة
        borrower = installment.loan.borrower
        
        if reminder_type == 'upcoming':
            subject = f'تذكير: قسط مستحق قريباً - القرض {installment.loan.loan_number}'
            message = f"""
            السيد/ة {borrower.name} المحترم/ة،
            
            نذكركم بأن لديكم قسط مستحق قريباً:
            
            - رقم القرض: {installment.loan.loan_number}
            - رقم القسط: {installment.installment_number}
            - تاريخ الاستحقاق: {installment.due_date}
            - المبلغ المستحق: {installment.remaining_amount} جنيه
            
            يرجى سداد القسط في الوقت المحدد لتجنب أي رسوم تأخير.
            
            شكراً لكم،
            إدارة Tony ERP
            """
        else:  # overdue
            days_overdue = (timezone.now().date() - installment.due_date).days
            subject = f'تنبيه: قسط متأخر - القرض {installment.loan.loan_number}'
            message = f"""
            السيد/ة {borrower.name} المحترم/ة،
            
            لديكم قسط متأخر عن الدفع:
            
            - رقم القرض: {installment.loan.loan_number}
            - رقم القسط: {installment.installment_number}
            - تاريخ الاستحقاق: {installment.due_date}
            - المبلغ المستحق: {installment.remaining_amount} جنيه
            - أيام التأخير: {days_overdue} يوم
            
            يرجى سداد القسط المتأخر في أقرب وقت ممكن.
            
            للاستفسار، يرجى الاتصال بنا.
            
            إدارة Tony ERP
            """
        
        # إرسال الرسالة (إذا كان البريد الإلكتروني مُعد)
        if borrower.email and settings.EMAIL_BACKEND != 'django.core.mail.backends.console.EmailBackend':
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'EMAIL_FROM', settings.DEFAULT_FROM_EMAIL),
                recipient_list=[borrower.email],
                fail_silently=False
            )
        
        # تحديث حالة التذكير
        reminder.status = 'sent'
        reminder.sent_at = timezone.now()
        reminder.save()
        
        logger.info(f"تم إرسال تذكير {reminder_type} للقسط {installment.id}")
        return True
        
    except Exception as e:
        if 'reminder' in locals():
            reminder.status = 'failed'
            reminder.error_message = str(e)
            reminder.save()
        
        logger.error(f"خطأ في إرسال تذكير القسط {installment.id}: {str(e)}")
        return False


@shared_task
def calculate_late_fees():
    """حساب رسوم التأخير للأقساط المتأخرة"""
    try:
        logger.info("بدء حساب رسوم التأخير")
        
        overdue_installments = LoanInstallment.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partially_paid']
        )
        
        updated_count = 0
        
        for installment in overdue_installments:
            days_overdue = (timezone.now().date() - installment.due_date).days
            
            # حساب رسوم التأخير (يمكن تخصيصها حسب نوع القرض)
            if days_overdue > 0 and not installment.late_fee_calculated:
                # مثال: 1% من المبلغ المستحق لكل أسبوع تأخير
                weeks_overdue = (days_overdue // 7) + 1
                late_fee_rate = 0.01  # 1%
                late_fee = installment.amount * (late_fee_rate * weeks_overdue)
                
                # تحديث المبلغ المستحق
                installment.late_fee = late_fee
                installment.late_fee_calculated = True
                installment.save()
                
                updated_count += 1
                
                logger.info(f"تم حساب رسوم تأخير للقسط {installment.id}: {late_fee}")
        
        logger.info(f"تم تحديث رسوم التأخير لـ {updated_count} قسط")
        return f"تم تحديث رسوم التأخير لـ {updated_count} قسط"
        
    except Exception as e:
        logger.error(f"خطأ في حساب رسوم التأخير: {str(e)}")
        raise


@shared_task
def generate_payment_reports():
    """إنشاء تقارير دورية للمدفوعات"""
    try:
        logger.info("بدء إنشاء تقارير المدفوعات")
        
        # إحصائيات الأقساط
        total_installments = LoanInstallment.objects.count()
        paid_installments = LoanInstallment.objects.filter(status='paid').count()
        overdue_installments = LoanInstallment.objects.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'partially_paid']
        ).count()
        
        stats = {
            'date': timezone.now().date().isoformat(),
            'total_installments': total_installments,
            'paid_installments': paid_installments,
            'overdue_installments': overdue_installments,
            'payment_rate': (paid_installments / total_installments * 100) if total_installments > 0 else 0
        }
        
        logger.info(f"إحصائيات المدفوعات: {stats}")
        
        return f"تم إنشاء تقرير المدفوعات لتاريخ {stats['date']}"
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء تقارير المدفوعات: {str(e)}")
        raise