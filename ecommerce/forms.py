"""
نماذج إدارة المتجر الإلكتروني
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    EcommerceSettings, OnlineProduct, ProductCategory, 
    PaymentGateway, ShippingCompany, SocialMediaIntegration,
    StorePageContent, StoreBanner, Coupon, SocialAuthProvider,
    ProductWarranty, WarrantyCard, WarrantyRegistration, WarrantyClaim
)


class EcommerceSettingsForm(forms.ModelForm):
    """نموذج إعدادات المتجر"""
    
    class Meta:
        model = EcommerceSettings
        fields = [
            'store_name', 'store_logo', 'store_description', 'currency',
            'products_per_page', 'show_out_of_stock', 'enable_reviews', 'enable_wishlist',
            'free_shipping_threshold', 'default_shipping_cost',
            'contact_email', 'contact_phone', 'whatsapp_number',
            # بالت الألوان
            'primary_color', 'secondary_color', 'accent_color',
            'background_color', 'text_color',
            'header_bg_color', 'header_text_color',
            'footer_bg_color', 'footer_text_color',
            'button_color', 'button_text_color', 'sale_badge_color',
            'is_active',
        ]
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المتجر'}),
            'store_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'وصف المتجر'}),
            'currency': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('EGP', 'جنيه مصري (EGP)'),
                ('AED', 'درهم إماراتي (AED)'),
                ('KWD', 'دينار كويتي (KWD)'),
                ('USD', 'دولار أمريكي (USD)'),
                ('EUR', 'يورو (EUR)'),
            ]),
            'products_per_page': forms.NumberInput(attrs={'class': 'form-control', 'min': 6, 'max': 48}),
            'free_shipping_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'default_shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+966 xx xxx xxxx'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+966 xx xxx xxxx'}),
            'show_out_of_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_reviews': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_wishlist': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # بالت الألوان
            'primary_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'background_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'text_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'header_bg_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'header_text_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'footer_bg_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'footer_text_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'button_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'button_text_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
            'sale_badge_color': forms.TextInput(attrs={'class': 'form-control form-control-color', 'type': 'color'}),
        }


class PaymentGatewayForm(forms.ModelForm):
    """نموذج بوابة الدفع"""
    
    class Meta:
        model = PaymentGateway
        fields = [
            'name', 'gateway_type', 'description', 'icon',
            'api_key', 'api_secret', 'merchant_id',
            'is_sandbox', 'sandbox_api_key', 'sandbox_api_secret',
            'is_active', 'sort_order',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم البوابة'}),
            'gateway_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'API Key'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'API Secret', 'autocomplete': 'new-password'}),
            'merchant_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Merchant ID'}),
            'sandbox_api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sandbox API Key'}),
            'sandbox_api_secret': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Sandbox API Secret', 'autocomplete': 'new-password'}),
            'is_sandbox': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إظهار القيم الحالية للحقول السرية
        if self.instance and self.instance.pk:
            if self.instance.api_secret:
                self.fields['api_secret'].widget.attrs['placeholder'] = '••••••••'
            if self.instance.sandbox_api_secret:
                self.fields['sandbox_api_secret'].widget.attrs['placeholder'] = '••••••••'


class ShippingCompanyForm(forms.ModelForm):
    """نموذج شركة الشحن"""
    
    class Meta:
        model = ShippingCompany
        fields = [
            'name', 'company_type', 'description', 'icon',
            'api_key', 'api_secret', 'account_number',
            'calculation_type', 'flat_rate', 'weight_rate', 'free_shipping_threshold',
            'tracking_url', 'is_sandbox', 'is_active', 'sort_order',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الشركة'}),
            'company_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'API Key'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'API Secret', 'autocomplete': 'new-password'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الحساب'}),
            'calculation_type': forms.Select(attrs={'class': 'form-select'}),
            'flat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'free_shipping_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tracking_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://track.example.com/{tracking_number}'}),
            'is_sandbox': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class SocialMediaIntegrationForm(forms.ModelForm):
    """نموذج تكامل التواصل الاجتماعي"""
    
    class Meta:
        model = SocialMediaIntegration
        fields = [
            'platform', 'profile_url', 'username',
            'app_id', 'app_secret', 'access_token', 'pixel_id',
            'enable_sharing', 'enable_login', 'enable_tracking',
            'show_in_header', 'show_in_footer',
            'is_active', 'sort_order',
        ]
        widgets = {
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'profile_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://facebook.com/yourpage'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '@username'}),
            'app_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'App ID'}),
            'app_secret': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'App Secret', 'autocomplete': 'new-password'}),
            'access_token': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Access Token'}),
            'pixel_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Facebook Pixel ID'}),
            'enable_sharing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_login': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_tracking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_in_header': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_in_footer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class StorePageContentForm(forms.ModelForm):
    """نموذج محتوى الصفحات"""
    
    class Meta:
        model = StorePageContent
        fields = ['title', 'content', 'meta_title', 'meta_description', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان الصفحة'}),
            'content': forms.Textarea(attrs={'class': 'form-control tinymce-editor', 'rows': 15}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان SEO'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'وصف SEO (أقصى 160 حرف)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class StoreBannerForm(forms.ModelForm):
    """نموذج البانر"""
    
    class Meta:
        model = StoreBanner
        fields = [
            'title', 'subtitle', 'image', 'image_mobile',
            'link_url', 'button_text', 'position',
            'start_date', 'end_date',
            'is_active', 'sort_order',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان البانر'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العنوان الفرعي'}),
            'link_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/offer'}),
            'button_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'تسوق الآن'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class CouponForm(forms.ModelForm):
    """نموذج الكوبون"""
    
    class Meta:
        model = Coupon
        fields = [
            'code', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount', 'usage_limit',
            'valid_from', 'valid_to', 'is_active',
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control text-uppercase', 'placeholder': 'SUMMER2024'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_discount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        return code.upper() if code else code


class ProductCategoryForm(forms.ModelForm):
    """نموذج فئة المنتج"""
    
    class Meta:
        model = ProductCategory
        fields = ['name', 'slug', 'description', 'image', 'parent', 'is_active', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم الفئة'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الرابط (يُملأ تلقائياً)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class OnlineProductForm(forms.ModelForm):
    """نموذج المنتج الإلكتروني"""
    
    class Meta:
        model = OnlineProduct
        fields = [
            'inventory_item', 'display_name', 'short_description', 'full_description',
            'category', 'main_image',
            'custom_price', 'discount_price', 'discount_start', 'discount_end',
            'is_featured', 'is_active', 'is_new',
            'meta_title', 'meta_description',
        ]
        widgets = {
            'inventory_item': forms.Select(attrs={'class': 'form-select'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العرض (اختياري)'}),
            'short_description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'وصف قصير'}),
            'full_description': forms.Textarea(attrs={'class': 'form-control tinymce-editor', 'rows': 8}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'custom_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'discount_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_new': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان SEO'}),
            'meta_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SocialAuthProviderForm(forms.ModelForm):
    """نموذج مزود تسجيل الدخول الاجتماعي"""
    
    class Meta:
        model = SocialAuthProvider
        fields = [
            'provider', 'name', 'client_id', 'client_secret',
            'auth_url', 'token_url', 'userinfo_url', 'scopes',
            'icon_class', 'button_color',
            'is_active', 'sort_order',
        ]
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم المعروض'}),
            'client_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Client ID'}),
            'client_secret': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Client Secret', 'render_value': True}),
            'auth_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'يتم ملؤه تلقائياً'}),
            'token_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'يتم ملؤه تلقائياً'}),
            'userinfo_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'يتم ملؤه تلقائياً'}),
            'scopes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'email profile'}),
            'icon_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fab fa-google'}),
            'button_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل بعض الحقول اختيارية - سيتم ملؤها تلقائياً
        self.fields['auth_url'].required = False
        self.fields['token_url'].required = False
        self.fields['userinfo_url'].required = False
        self.fields['scopes'].required = False
        self.fields['icon_class'].required = False
        self.fields['button_color'].required = False


# ==================== نماذج الإعدادات الجديدة ====================

from .models import (
    HeaderSettings, FooterSettings, HeaderLink, FooterColumn, FooterLink,
    NewsletterSubscriber, NewsletterCampaign, FlashSale, FlashSaleProduct,
    HomepageSection, HomepageSectionProduct, SidebarCategory,
    ShippingZone, ShippingRate
)


class HeaderSettingsForm(forms.ModelForm):
    """نموذج إعدادات الهيدر"""
    
    class Meta:
        model = HeaderSettings
        fields = [
            'logo', 'logo_alt_text', 'favicon',
            'top_bar_text', 'top_bar_enabled',
            'header_bg_color', 'header_text_color', 'top_bar_bg_color',
            'show_search', 'show_cart', 'show_wishlist', 'show_account', 'show_language',
            'sticky_header',
        ]
        widgets = {
            'logo_alt_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'النص البديل للشعار'}),
            'top_bar_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شحن مجاني للطلبات فوق 200 ج.م'}),
            'top_bar_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'header_bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'header_text_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'top_bar_bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'show_search': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_cart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_wishlist': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_account': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_language': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sticky_header': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class FooterSettingsForm(forms.ModelForm):
    """نموذج إعدادات الفوتر"""
    
    class Meta:
        model = FooterSettings
        fields = [
            'footer_logo', 'footer_description',
            'footer_bg_color', 'footer_text_color',
            'copyright_text',
            'show_newsletter', 'show_social_links', 'show_payment_icons', 'show_app_links',
            'app_store_link', 'play_store_link',
        ]
        widgets = {
            'footer_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'footer_bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'footer_text_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'copyright_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '© 2024 جميع الحقوق محفوظة'}),
            'show_newsletter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_social_links': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_payment_icons': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_app_links': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'app_store_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'رابط App Store'}),
            'play_store_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'رابط Play Store'}),
        }


class HeaderLinkForm(forms.ModelForm):
    """نموذج رابط الهيدر"""
    
    class Meta:
        model = HeaderLink
        fields = ['title', 'url', 'icon', 'open_new_tab', 'sort_order', 'is_active', 'parent']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان الرابط'}),
            'url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/products/ أو https://...'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-home'}),
            'open_new_tab': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
        }


class FlashSaleForm(forms.ModelForm):
    """نموذج العرض السريع"""
    
    class Meta:
        model = FlashSale
        fields = [
            'name', 'description',
            'start_date', 'end_date',
            'discount_type', 'discount_value',
            'banner',
            'is_active', 'show_countdown',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم العرض'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_countdown': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class HomepageSectionForm(forms.ModelForm):
    """نموذج قسم الصفحة الرئيسية"""
    
    class Meta:
        model = HomepageSection
        fields = [
            'title', 'subtitle',
            'section_type', 'display_style',
            'category', 'products_count',
            'custom_html',
            'sort_order', 'is_active',
            'show_view_all', 'view_all_url',
            'bg_color', 'bg_image',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان القسم'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'العنوان الفرعي'}),
            'section_type': forms.Select(attrs={'class': 'form-select'}),
            'display_style': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'products_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 24}),
            'custom_html': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_view_all': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'view_all_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/products/'}),
            'bg_color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }


class SidebarCategoryForm(forms.ModelForm):
    """نموذج فئة الشريط الجانبي"""
    
    class Meta:
        model = SidebarCategory
        fields = ['category', 'sort_order', 'is_active', 'show_icon', 'custom_icon']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_icon': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'fas fa-box'}),
        }


class ShippingZoneForm(forms.ModelForm):
    """نموذج منطقة الشحن"""
    
    class Meta:
        model = ShippingZone
        fields = ['name', 'countries', 'cities', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المنطقة'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NewsletterCampaignForm(forms.ModelForm):
    """نموذج الحملة البريدية"""
    from .models import NewsletterCampaign
    
    class Meta:
        from .models import NewsletterCampaign
        model = NewsletterCampaign
        fields = ['subject', 'content', 'scheduled_at']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'موضوع البريد الإلكتروني'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'محتوى الرسالة البريدية...'
            }),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'subject': 'موضوع البريد',
            'content': 'محتوى الرسالة',
            'scheduled_at': 'موعد الإرسال (اختياري)',
        }


class ShippingRateForm(forms.ModelForm):
    """نموذج سعر الشحن"""
    
    class Meta:
        model = ShippingRate
        fields = [
            'zone', 'company',
            'rate_type', 'flat_rate', 'weight_rate', 'min_order_free',
            'delivery_time_min', 'delivery_time_max',
            'is_active',
        ]
        widgets = {
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'rate_type': forms.Select(attrs={'class': 'form-select'}),
            'flat_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_order_free': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_time_min': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'delivery_time_max': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# =====================================================
# نماذج الضمان - Warranty Forms
# =====================================================

class ProductWarrantyForm(forms.ModelForm):
    """نموذج سياسة الضمان"""
    
    class Meta:
        model = ProductWarranty
        fields = [
            'name', 'description', 'duration', 'duration_unit',
            'terms_and_conditions', 'coverage', 'exclusions',
            'requires_registration', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: ضمان سنة كاملة'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'وصف مختصر للضمان'
            }),
            'duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': '12'
            }),
            'duration_unit': forms.Select(attrs={'class': 'form-select'}),
            'terms_and_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'شروط وأحكام الضمان'
            }),
            'coverage': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'ما يغطيه الضمان (مثال: عيوب التصنيع، الأعطال الفنية...)'
            }),
            'exclusions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'ما لا يغطيه الضمان (مثال: سوء الاستخدام، التلف المتعمد...)'
            }),
            'requires_registration': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WarrantyCardForm(forms.ModelForm):
    """نموذج بطاقة الضمان"""
    
    class Meta:
        model = WarrantyCard
        fields = [
            'product', 'inventory_product', 'warranty_policy',
            'serial_number', 'purchase_date', 'status',
        ]
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'inventory_product': forms.Select(attrs={'class': 'form-select'}),
            'warranty_policy': forms.Select(attrs={'class': 'form-select'}),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم التسلسلي للمنتج'
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class WarrantyRegistrationForm(forms.ModelForm):
    """نموذج تسجيل الضمان من العميل"""
    
    class Meta:
        model = WarrantyRegistration
        fields = [
            'customer_name', 'customer_email', 'customer_phone', 'customer_address',
            'warranty_code_entered', 'invoice_number', 'invoice_image',
            'purchase_date', 'product_serial', 'product_image',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم الكامل',
                'required': True
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com',
                'required': True
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+966 5xx xxx xxx',
                'required': True
            }),
            'customer_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'العنوان (اختياري)'
            }),
            'warranty_code_entered': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'أدخل رمز الضمان أو امسح QR Code',
                'id': 'warranty-code-input'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'رقم الفاتورة'
            }),
            'invoice_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'required': True
            }),
            'purchase_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'product_serial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الرقم التسلسلي للمنتج (إن وجد)'
            }),
            'product_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean_warranty_code_entered(self):
        code = self.cleaned_data.get('warranty_code_entered', '').strip().upper()
        if not code:
            raise forms.ValidationError('يرجى إدخال رمز الضمان')
        
        # التحقق من وجود البطاقة
        try:
            warranty_card = WarrantyCard.objects.get(warranty_code=code)
            if warranty_card.status == 'active':
                raise forms.ValidationError('هذا الضمان مفعل بالفعل')
            elif warranty_card.status == 'void':
                raise forms.ValidationError('رمز الضمان هذا ملغي')
            elif warranty_card.status == 'expired':
                raise forms.ValidationError('انتهت صلاحية هذا الضمان')
        except WarrantyCard.DoesNotExist:
            raise forms.ValidationError('رمز الضمان غير صحيح')
        
        return code


class WarrantyClaimForm(forms.ModelForm):
    """نموذج مطالبة الضمان"""
    
    class Meta:
        model = WarrantyClaim
        fields = [
            'claim_type', 'issue_description', 'issue_images',
            'contact_name', 'contact_phone', 'contact_email', 'pickup_address',
        ]
        widgets = {
            'claim_type': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'اشرح المشكلة بالتفصيل...',
                'required': True
            }),
            'issue_images': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'الاسم للتواصل',
                'required': True
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+966 5xx xxx xxx',
                'required': True
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'pickup_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'عنوان استلام المنتج'
            }),
        }


class WarrantySearchForm(forms.Form):
    """نموذج البحث عن الضمان"""
    warranty_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'أدخل رمز الضمان أو امسح QR Code',
            'id': 'warranty-search-input'
        }),
        label='رمز الضمان'
    )


class WarrantyReviewForm(forms.Form):
    """نموذج مراجعة تسجيل الضمان من الإدارة"""
    action = forms.ChoiceField(
        choices=[
            ('approve', 'موافقة'),
            ('reject', 'رفض'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'ملاحظات (مطلوبة في حالة الرفض)'
        }),
        label='ملاحظات المراجعة'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        notes = cleaned_data.get('notes')
        
        if action == 'reject' and not notes:
            raise forms.ValidationError('يجب إدخال سبب الرفض')
        
        return cleaned_data
