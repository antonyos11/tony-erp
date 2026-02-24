"""
نماذج النظام الأساسي
"""
from django import forms
from .models import Currency, Company, AppSettings, Country, State, Branch, Page, CompanyPhone, CompanyPhone


class CurrencyForm(forms.ModelForm):
    """نموذج إدارة العملات"""
    
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'exchange_rate', 'decimal_places', 'is_active', 'is_default']
        widgets = {
            'code': forms.Select(choices=Currency.CURRENCY_CODES, attrs={
                'class': 'form-control',
                'dir': 'ltr'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم العملة'
            }),
            'symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رمز العملة (مثل: ج.م)',
                'dir': 'ltr'
            }),
            'exchange_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.000001',
                'min': '0.000001',
                'placeholder': '1.000000'
            }),
            'decimal_places': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '6',
                'placeholder': '2'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'code': 'رمز العملة',
            'name': 'اسم العملة',
            'symbol': 'رمز العرض',
            'exchange_rate': 'سعر الصرف',
            'decimal_places': 'عدد الخانات العشرية',
            'is_active': 'نشطة',
            'is_default': 'افتراضية'
        }
        help_texts = {
            'exchange_rate': 'سعر الصرف مقابل العملة الافتراضية (مثال: 1 دولار = 31 جنيه)',
            'decimal_places': 'عدد الأرقام بعد العلامة العشرية',
            'is_default': 'العملة المستخدمة كأساس في النظام (عملة واحدة فقط)'
        }

    def clean_exchange_rate(self):
        exchange_rate = self.cleaned_data['exchange_rate']
        if exchange_rate <= 0:
            raise forms.ValidationError('سعر الصرف يجب أن يكون أكبر من الصفر')
        return exchange_rate

    def clean_decimal_places(self):
        decimal_places = self.cleaned_data['decimal_places']
        if decimal_places < 0 or decimal_places > 6:
            raise forms.ValidationError('عدد الخانات العشرية يجب أن يكون بين 0 و 6')
        return decimal_places

    def clean(self):
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        is_active = cleaned_data.get('is_active')
        
        # التأكد من أن العملة الافتراضية نشطة
        if is_default and not is_active:
            raise forms.ValidationError('العملة الافتراضية يجب أن تكون نشطة')
        
        return cleaned_data


class CompanySettingsForm(forms.ModelForm):
    """نموذج إعدادات الشركة"""
    
    class Meta:
        model = Company
        fields = ['name', 'address', 'phone', 'mobile', 'email', 'tax_id', 'commercial_register',
                  'logo', 'invoice_prefix', 'default_currency', 'slogan', 'footer_text',
                  'website', 'facebook', 'instagram', 'twitter', 'whatsapp',
                  'tiktok', 'youtube', 'linkedin', 'default_vat_rate']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم الشركة'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'عنوان الشركة'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف الرئيسي'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الموبايل'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'البريد الإلكتروني'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم الضريبي'
            }),
            'commercial_register': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم السجل التجاري'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'invoice_prefix': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: INV'
            }),
            'default_currency': forms.Select(attrs={
                'class': 'form-control'
            }),
            'slogan': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شعار الشركة النصي (يظهر على المطبوعات)'
            }),
            'footer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'نص يظهر أسفل الفواتير والمطبوعات'
            }),
            'default_vat_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': '14.00'
            }),
        }
        labels = {
            'name': 'اسم الشركة',
            'address': 'العنوان',
            'phone': 'رقم الهاتف الرئيسي',
            'mobile': 'الموبايل',
            'email': 'البريد الإلكتروني',
            'tax_id': 'الرقم الضريبي',
            'commercial_register': 'السجل التجاري',
            'logo': 'شعار الشركة',
            'invoice_prefix': 'بداية رقم الفاتورة',
            'default_currency': 'العملة الافتراضية',
            'slogan': 'شعار الشركة النصي',
            'footer_text': 'نص تذييل المطبوعات',
            'default_vat_rate': 'نسبة ضريبة القيمة المضافة %',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديد العملات النشطة فقط
        self.fields['default_currency'].queryset = Currency.objects.filter(is_active=True)


class CurrencyExchangeRateForm(forms.Form):
    """نموذج تحديث أسعار الصرف"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # إضافة حقول أسعار الصرف للعملات النشطة غير الافتراضية
        non_default_currencies = Currency.objects.filter(is_active=True, is_default=False)
        
        for currency in non_default_currencies:
            self.fields[f'rate_{currency.code}'] = forms.DecimalField(
                label=f'سعر {currency.name}',
                initial=currency.exchange_rate,
                max_digits=15,
                decimal_places=6,
                min_value=0.000001,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'step': '0.000001',
                    'placeholder': f'{currency.exchange_rate}'
                })
            )

    def save(self):
        """حفظ أسعار الصرف الجديدة"""
        for field_name, rate in self.cleaned_data.items():
            if field_name.startswith('rate_'):
                currency_code = field_name.replace('rate_', '')
                try:
                    currency = Currency.objects.get(code=currency_code, is_active=True)
                    currency.exchange_rate = rate
                    currency.save()
                except Currency.DoesNotExist:
                    continue


class CountryForm(forms.ModelForm):
    """نموذج الدول"""
    
    class Meta:
        model = Country
        fields = ['name', 'name_en', 'code', 'phone_code', 'currency', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الدولة'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country Name', 'dir': 'ltr'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EG', 'dir': 'ltr', 'maxlength': '3'}),
            'phone_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+20', 'dir': 'ltr'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.filter(is_active=True)


class StateForm(forms.ModelForm):
    """نموذج المحافظات"""
    
    class Meta:
        model = State
        fields = ['name', 'name_en', 'country', 'code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المحافظة'}),
            'name_en': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State Name', 'dir': 'ltr'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CAI', 'dir': 'ltr'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].queryset = Country.objects.filter(is_active=True)


class BranchForm(forms.ModelForm):
    """نموذج الفروع"""
    
    class Meta:
        model = Branch
        fields = ['name', 'code', 'country', 'state', 'address', 'phone', 'email', 'is_main', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الفرع'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BR001', 'dir': 'ltr'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'العنوان التفصيلي'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com', 'dir': 'ltr'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].queryset = Country.objects.filter(is_active=True).order_by('name')
        # Limit states to the selected country to avoid loading all world subdivisions at once
        self.fields['state'].queryset = State.objects.none()
        self.fields['state'].required = False

        selected_country_id = None
        if self.data.get('country'):
            try:
                selected_country_id = int(self.data.get('country'))
            except (TypeError, ValueError):
                selected_country_id = None
        elif self.instance and getattr(self.instance, 'country_id', None):
            selected_country_id = self.instance.country_id

        if selected_country_id:
            self.fields['state'].queryset = State.objects.filter(
                is_active=True,
                country_id=selected_country_id
            ).order_by('name')


class PageForm(forms.ModelForm):
    """نموذج الصفحات"""
    
    class Meta:
        model = Page
        fields = ['name', 'code', 'url', 'parent', 'icon', 'order', 'is_active', 'is_menu_item']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الصفحة'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'page_code', 'dir': 'ltr'}),
            'url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/path/to/page/', 'dir': 'ltr'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bi-house', 'dir': 'ltr'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_menu_item': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = Page.objects.filter(is_active=True)
        self.fields['parent'].required = False


class CompanyPhoneForm(forms.ModelForm):
    """نموذج رقم هاتف الشركة"""
    
    class Meta:
        model = CompanyPhone
        fields = ['phone_type', 'phone_number', 'contact_person',
                  'is_active', 'show_on_print', 'show_on_store', 'sort_order']
        widgets = {
            'phone_type': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الهاتف'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'اسم المسؤول (اختياري)'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_on_print': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_on_store': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'style': 'width:70px'}),
        }


CompanyPhoneFormSet = forms.inlineformset_factory(
    Company, CompanyPhone,
    form=CompanyPhoneForm,
    extra=1,
    can_delete=True,
)