"""
إشارات نظام التقسيط - Installments Signals
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import InstallmentContract, Installment, InstallmentPayment


@receiver(post_save, sender=InstallmentContract)
def on_contract_approved(sender, instance, created, **kwargs):
    """عند اعتماد العقد، توليد جدول الأقساط"""
    if instance.status == 'approved' and not instance.installments.exists():
        instance.generate_installments()
        instance.status = 'active'
        instance.approved_at = timezone.now()
        instance.save(update_fields=['status', 'approved_at'])


@receiver(pre_save, sender=Installment)
def update_installment_status(sender, instance, **kwargs):
    """تحديث حالة القسط تلقائياً"""
    if instance.status not in ['paid', 'waived']:
        if instance.is_overdue:
            instance.status = 'overdue'
            instance.late_fee = instance.calculate_late_fee()


@receiver(post_save, sender=InstallmentPayment)
def on_payment_received(sender, instance, created, **kwargs):
    """عند استلام دفعة، إنشاء قيد محاسبي (اختياري)"""
    if not created:
        return
    # التكامل المحاسبي اختياري ويُفعّل عند توفر الخدمة
    try:
        from accounting.services.journal_service import create_journal_entry  # type: ignore
    except Exception:
        return

    contract = instance.installment.contract
    # TODO: ربط create_journal_entry بمعاملات الأقساط حسب إعدادات الحسابات
    # مثال تقريبي:
    # create_journal_entry(
    #     description=f"Installment payment {instance.receipt_number}",
    #     debit_account=..., credit_account=..., amount=instance.amount,
    #     partner=contract.customer, reference=contract.contract_number,
    # )


def check_overdue_installments():
    """مهمة دورية لفحص الأقساط المتأخرة"""
    from datetime import date
    
    today = date.today()
    
    # تحديث الأقساط المتأخرة
    overdue_installments = Installment.objects.filter(
        status__in=['pending', 'partially_paid'],
        due_date__lt=today
    )
    
    for installment in overdue_installments:
        if installment.is_overdue:
            installment.status = 'overdue'
            installment.late_fee = installment.calculate_late_fee()
            installment.save(update_fields=['status', 'late_fee', 'updated_at'])
    
    # تحديث العقود المتعثرة
    from .models import InstallmentSettings
    settings = InstallmentSettings.get_settings()
    
    contracts_to_check = InstallmentContract.objects.filter(status='active')
    
    for contract in contracts_to_check:
        # إذا كان هناك قسط متأخر أكثر من الحد المسموح
        oldest_overdue = contract.installments.filter(
            status='overdue'
        ).order_by('due_date').first()
        
        if oldest_overdue:
            days_overdue = (today - oldest_overdue.due_date).days
            if days_overdue >= settings.default_after_days:
                contract.status = 'defaulted'
                contract.save(update_fields=['status', 'updated_at'])


def send_installment_reminders():
    """مهمة دورية لإرسال التذكيرات"""
    from datetime import date, timedelta
    from .models import InstallmentSettings, InstallmentReminder
    
    settings = InstallmentSettings.get_settings()
    
    if not settings.auto_reminders_enabled:
        return
    
    today = date.today()
    
    # تذكيرات قبل الاستحقاق
    upcoming_date = today + timedelta(days=settings.reminder_days_before)
    upcoming_installments = Installment.objects.filter(
        status='pending',
        due_date=upcoming_date,
        reminder_count=0
    )
    
    for installment in upcoming_installments:
        _send_reminder(installment, 'upcoming', settings)
    
    # تذكيرات يوم الاستحقاق
    due_today = Installment.objects.filter(
        status='pending',
        due_date=today
    ).exclude(
        reminders__reminder_type='due'
    )
    
    for installment in due_today:
        _send_reminder(installment, 'due', settings)
    
    # تذكيرات التأخير
    overdue_installments = Installment.objects.filter(
        status='overdue',
        reminder_count__lt=settings.max_reminders_per_installment
    )
    
    for installment in overdue_installments:
        # التحقق من الفترة منذ آخر تذكير
        if installment.last_reminder_date:
            days_since_last = (timezone.now() - installment.last_reminder_date).days
            if days_since_last < settings.overdue_reminder_interval:
                continue
        
        _send_reminder(installment, 'overdue', settings)


def _send_reminder(installment, reminder_type, settings):
    """إرسال تذكير للقسط"""
    from .models import InstallmentReminder
    
    contract = installment.contract
    customer = contract.customer
    
    # اختيار قالب الرسالة
    if reminder_type == 'upcoming':
        template = settings.upcoming_message_template
    elif reminder_type == 'due':
        template = settings.due_message_template
    else:
        template = settings.overdue_message_template
    
    # تنسيق الرسالة
    message = template.format(
        customer_name=customer.name,
        installment_number=installment.installment_number,
        amount=installment.amount,
        due_date=installment.due_date.strftime('%Y-%m-%d'),
        contract_number=contract.contract_number,
        days_overdue=installment.days_overdue,
        late_fee=installment.late_fee,
    )
    
    # إرسال عبر القنوات المفعلة
    channels = []
    if settings.whatsapp_enabled:
        channels.append('whatsapp')
    if settings.sms_enabled:
        channels.append('sms')
    if settings.email_enabled:
        channels.append('email')
    if settings.push_enabled:
        channels.append('push')
    
    for channel in channels:
        InstallmentReminder.objects.create(
            installment=installment,
            reminder_type=reminder_type,
            channel=channel,
            message=message,
            delivered=True  # سيتم تحديثه من النظام الفعلي
        )
    
    # تحديث عداد التذكيرات
    installment.reminder_count += 1
    installment.last_reminder_date = timezone.now()
    installment.save(update_fields=['reminder_count', 'last_reminder_date'])
