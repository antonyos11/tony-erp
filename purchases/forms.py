from django import forms
from inventory.models import SupplierProductPrice, Product
from partners.models import Supplier
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

# Use the same UOM choices as Product model (single source of truth)
UOM_CHOICES = Product.UOM_CHOICES


class SupplierProductPriceForm(forms.Form):
    """نموذج بسيط لإضافة وتعديل أسعار المواد الخام حسب المورد"""

    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.order_by('name'),
        label=_('المورد'),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
        })
    )

    # وضع الإدخال: اختيار موجودة أو إضافة جديدة
    MATERIAL_MODE_CHOICES = [
        ('existing', 'اختر مادة موجودة'),
        ('new', 'أضف مادة خام جديدة الآن'),
    ]
    material_mode = forms.ChoiceField(
        choices=MATERIAL_MODE_CHOICES,
        initial='existing',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'material-mode-radio'}),
    )

    # المادة الخام - اختيار من المنتجات الموجودة
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(
            product_type='raw_material', is_active=True
        ).order_by('name'),
        label=_('المادة الخام'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'id_product',
        })
    )

    # اسم مادة خام جديدة (يُستخدم عند material_mode == 'new')
    new_material_name = forms.CharField(
        label=_('اسم المادة الخام الجديدة'),
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'مثال: اسفنج كثافة 26',
            'autocomplete': 'off',
        })
    )

    purchase_unit = forms.ChoiceField(
        label=_('وحدة الشراء'),
        choices=UOM_CHOICES,
        initial='unit',
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'id_purchase_unit',
        })
    )

    cost = forms.DecimalField(
        label=_('السعر'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-lg',
            'step': '0.01',
            'min': '0',
            'placeholder': 'سعر الوحدة',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('material_mode', 'existing')
        product = cleaned_data.get('product')
        new_name = (cleaned_data.get('new_material_name') or '').strip()

        if mode == 'new':
            if not new_name:
                self.add_error('new_material_name', 'يرجى إدخال اسم المادة الخام الجديدة.')
        else:
            if not product:
                self.add_error('product', 'يرجى اختيار المادة الخام.')

        return cleaned_data

