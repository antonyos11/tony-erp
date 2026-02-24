from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import (
    Customer, ContactPerson, Opportunity, Activity,
    Quotation, QuotationItem, SupportTicket, Campaign
)
from inventory.models import Product

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'company_name', 'phone', 'mobile',
            'email', 'website', 'address_line1', 'address_line2', 'city', 'state', 'postal_code',
            'customer_type', 'source', 'assigned_to', 'credit_limit',
            'payment_terms', 'tax_number', 'notes', 'status'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الأول'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الأخير'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الشركة'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '02xxxxxxxx'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '01xxxxxxxxx'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@company.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.company.com'
            }),
            'address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'العنوان الأول'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'العنوان الثاني (اختياري)'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المحافظة'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المدينة'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرمز البريدي'
            }),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'payment_terms': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '30 يوم، دفع فوري، إلخ'
            }),
            'tax_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم الضريبي'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'first_name': 'الاسم الأول',
            'last_name': 'الاسم الأخير',
            'company_name': 'اسم الشركة',
            'phone': 'الهاتف الثابت',
            'mobile': 'الهاتف المحمول',
            'email': 'البريد الإلكتروني',
            'website': 'الموقع الإلكتروني',
            'address_line1': 'العنوان الأول',
            'address_line2': 'العنوان الثاني',
            'state': 'المحافظة',
            'city': 'المدينة',
            'postal_code': 'الرمز البريدي',
            'customer_type': 'نوع العميل',
            'source': 'مصدر العميل',
            'assigned_to': 'مسؤول المبيعات',
            'credit_limit': 'حد الائتمان',
            'payment_terms': 'مدة السداد (بالأيام)',
            'tax_number': 'الرقم الضريبي',
            'notes': 'الملاحظات',
            'status': 'الحالة',
        }

class ContactPersonForm(forms.ModelForm):
    class Meta:
        model = ContactPerson
        fields = [
            'name', 'position', 'phone', 'mobile', 'email',
            'is_primary', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم جهة الاتصال'
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'المنصب'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '02xxxxxxxx'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '01xxxxxxxxx'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@company.com'
            }),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات'
            }),
        }

class OpportunityForm(forms.ModelForm):
    class Meta:
        model = Opportunity
        fields = [
            'name', 'customer', 'contact_person', 'estimated_value',
            'expected_close_date', 'stage', 'priority', 'assigned_to',
            'description', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الفرصة التجارية'
            }),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.Select(attrs={'class': 'form-select'}),
            'estimated_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'expected_close_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'وصف الفرصة التجارية'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'ملاحظات إضافية'
            }),
        }
    
    def clean_estimated_value(self):
        value = self.cleaned_data.get('estimated_value')
        if value is not None and value < 0:
            raise forms.ValidationError('القيمة المقدرة يجب أن تكون موجبة')
        if value is not None and value == 0:
            raise forms.ValidationError('القيمة المقدرة يجب أن تكون أكبر من صفر')
        return value
    
    def clean_expected_close_date(self):
        from django.utils import timezone
        date = self.cleaned_data.get('expected_close_date')
        if date and date < timezone.now().date():
            raise forms.ValidationError('التاريخ المتوقع للإغلاق يجب أن يكون في المستقبل')
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        contact_person = cleaned_data.get('contact_person')
        
        # Validate contact person belongs to customer
        if customer and contact_person:
            if contact_person.customer_id != customer.id:
                raise forms.ValidationError({
                    'contact_person': 'جهة الاتصال المختارة لا تنتمي للعميل المحدد'
                })
        
        return cleaned_data

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            'title', 'customer', 'contact_person', 'opportunity', 'activity_type',
            'scheduled_date', 'duration_minutes', 'priority',
            'assigned_to', 'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان النشاط'
            }),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.Select(attrs={'class': 'form-select'}),
            'opportunity': forms.Select(attrs={'class': 'form-select'}),
            'activity_type': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '60',
                'min': '15',
                'step': '15'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'وصف النشاط'
            }),
        }

class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = [
            'customer', 'opportunity', 'quotation_date', 'valid_until',
            'discount_percentage', 'tax_percentage', 'terms_and_conditions',
            'notes', 'status'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'opportunity': forms.Select(attrs={'class': 'form-select'}),
            'quotation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'tax_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '14.00'
            }),
            'terms_and_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'الشروط والأحكام'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ملاحظات إضافية'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_discount_percentage(self):
        value = self.cleaned_data.get('discount_percentage')
        if value is not None:
            if value < 0:
                raise forms.ValidationError('نسبة الخصم لا يمكن أن تكون سالبة')
            if value > 100:
                raise forms.ValidationError('نسبة الخصم لا يمكن أن تتجاوز 100%')
        return value
    
    def clean_tax_percentage(self):
        value = self.cleaned_data.get('tax_percentage')
        if value is not None:
            if value < 0:
                raise forms.ValidationError('نسبة الضريبة لا يمكن أن تكون سالبة')
            if value > 100:
                raise forms.ValidationError('نسبة الضريبة لا يمكن أن تتجاوز 100%')
        return value
    
    def clean(self):
        cleaned_data = super().clean()
        quotation_date = cleaned_data.get('quotation_date')
        valid_until = cleaned_data.get('valid_until')
        customer = cleaned_data.get('customer')
        opportunity = cleaned_data.get('opportunity')
        
        # Validate dates
        if quotation_date and valid_until:
            if valid_until < quotation_date:
                raise forms.ValidationError({
                    'valid_until': 'تاريخ الصلاحية يجب أن يكون بعد تاريخ العرض'
                })
        
        # Validate opportunity belongs to customer
        if customer and opportunity:
            if opportunity.customer_id != customer.id:
                raise forms.ValidationError({
                    'opportunity': 'الفرصة المختارة لا تنتمي للعميل المحدد'
                })
        
        return cleaned_data

class QuotationItemForm(forms.ModelForm):
    class Meta:
        model = QuotationItem
        fields = ['product', 'description', 'quantity', 'unit_price', 'discount_percentage', 'tax_percentage']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'وصف المنتج (اختياري)'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control price-input',
                'step': '0.01',
                'min': '0'
            }),
            'discount_percentage': forms.NumberInput(attrs={
                'class': 'form-control item-discount-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
            'tax_percentage': forms.NumberInput(attrs={
                'class': 'form-control item-tax-input',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '0.00'
            }),
        }

# Formset مخصص لاكتشاف وجود خصم/ضريبة على مستوى الأصناف (لأغراض التحذير فقط)
class CustomQuotationItemFormSet(BaseInlineFormSet):
    has_line_discount: bool = False
    has_line_tax: bool = False

    def clean(self):
        super().clean()
        self.has_line_discount = False
        self.has_line_tax = False
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            cd = form.cleaned_data or {}
            # تخطي الصفوف المحذوفة
            if cd.get('DELETE'):
                continue
            dp = cd.get('discount_percentage') or 0
            tp = cd.get('tax_percentage') or 0
            try:
                self.has_line_discount = self.has_line_discount or (float(dp) > 0)
                self.has_line_tax = self.has_line_tax or (float(tp) > 0)
            except (TypeError, ValueError):
                # إذا كانت القيم غير قابلة للتحويل نتجاوز (سيتم التعامل معها عبر التحقق الاعتيادي)
                pass

# إنشاء formset لأصناف عرض السعر باستخدام الـ Formset المخصص
QuotationItemFormSet = inlineformset_factory(
    Quotation,
    QuotationItem,
    form=QuotationItemForm,
    formset=CustomQuotationItemFormSet,
    extra=5,
    can_delete=True,
    min_num=1,
    validate_min=True
)

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = [
            'title', 'customer', 'category', 'description',
            'priority', 'assigned_to'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان التذكرة'
            }),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'وصف تفصيلي للمشكلة أو الطلب'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = [
            'name', 'campaign_type', 'customer_type', 'target_customers',
            'description', 'message_content', 'budget', 'start_date',
            'end_date', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الحملة'
            }),
            'campaign_type': forms.Select(attrs={'class': 'form-select'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'target_customers': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': '8'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'وصف الحملة'
            }),
            'message_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'محتوى رسالة الحملة'
            }),
            'budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

# نموذج لتعليقات التذاكر
class TicketCommentForm(forms.Form):
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'اكتب تعليقك هنا...'
        }),
        label='التعليق',
        required=True
    )
    is_internal = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='تعليق داخلي (للموظفين فقط)',
        required=False
    )

# نموذج البحث السريع
class QuickSearchForm(forms.Form):
    query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'البحث في العملاء والفرص...',
            'autocomplete': 'off'
        }),
        required=False
    )

# نموذج فلاتر متقدمة
class AdvancedFilterForm(forms.Form):
    PRIORITY_CHOICES = [
        ('', 'جميع الأولويات'),
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
        ('urgent', 'عاجل'),
    ]
    
    STATUS_CHOICES = [
        ('', 'جميع الحالات'),
        ('active', 'نشط'),
        ('inactive', 'غير نشط'),
        ('pending', 'في الانتظار'),
    ]
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='من تاريخ'
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False,
        label='إلى تاريخ'
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='الأولوية'
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        label='الحالة'
    )